"""
Listing Monitor — 업비트/빗썸 신규 상장 실시간 감지 → 텔레그램 알림.
1분 간격 폴링, coin_listing UPSERT + listing_event INSERT.
"""
import os
import json
import time
import logging
import urllib.request
from datetime import datetime, timezone, timedelta

import psycopg2
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "app")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))
BOOTSTRAP_MODE = os.getenv("BOOTSTRAP_MODE", "false").lower() == "true"

KST = timezone(timedelta(hours=9))

UPSERT_SQL = """
    INSERT INTO coin_listing (exchange, symbol, market_code, korean_name, english_name,
                              first_seen_date, is_active, updated_at)
    VALUES (%s, %s, %s, %s, %s, CURRENT_DATE, TRUE, NOW())
    ON CONFLICT (exchange, symbol) DO UPDATE SET
        market_code = EXCLUDED.market_code,
        korean_name = COALESCE(EXCLUDED.korean_name, coin_listing.korean_name),
        english_name = COALESCE(EXCLUDED.english_name, coin_listing.english_name),
        is_active = TRUE,
        updated_at = NOW()
"""

INSERT_EVENT_SQL = """
    INSERT INTO listing_event (exchange, symbol, market_code, korean_name, english_name, notified)
    VALUES (%s, %s, %s, %s, %s, %s)
"""


def connect_db():
    """DB 연결 (재시도 로직)."""
    for attempt in range(1, 11):
        try:
            conn = psycopg2.connect(
                host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
                user=DB_USER, password=DB_PASSWORD,
            )
            conn.autocommit = False
            logger.info("DB 연결 성공")
            return conn
        except psycopg2.OperationalError as e:
            logger.warning(f"DB 연결 실패 (시도 {attempt}/10): {e}")
            time.sleep(5)
    raise RuntimeError("DB 연결 10회 실패")


def send_telegram(message: str):
    """텔레그램 메시지 전송 (urllib 패턴)."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning(f"텔레그램 미설정. 메시지: {message}")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.getcode() != 200:
                logger.error(f"텔레그램 전송 실패: {resp.read()}")
    except Exception as e:
        logger.error(f"텔레그램 오류: {e}")


def fetch_upbit():
    """업비트 KRW 마켓 종목 조회."""
    resp = requests.get(
        "https://api.upbit.com/v1/market/all",
        params={"is_details": "false"},
        timeout=10,
    )
    resp.raise_for_status()
    coins = []
    for m in resp.json():
        code = m["market"]
        if not code.startswith("KRW-"):
            continue
        symbol = code.split("-")[1]
        coins.append({
            "exchange": "upbit",
            "symbol": symbol,
            "market_code": code,
            "korean_name": m.get("korean_name"),
            "english_name": m.get("english_name"),
        })
    return coins


def fetch_bithumb():
    """빗썸 KRW 마켓 종목 조회."""
    resp = requests.get("https://api.bithumb.com/public/ticker/ALL_KRW", timeout=10)
    resp.raise_for_status()
    data = resp.json().get("data", {})
    coins = []
    for sym, info in data.items():
        if sym == "date" or not isinstance(info, dict):
            continue
        coins.append({
            "exchange": "bithumb",
            "symbol": sym,
            "market_code": f"{sym}_KRW",
            "korean_name": None,
            "english_name": None,
        })
    return coins


def load_known_markets(conn):
    """DB에서 기존 (exchange, symbol) 세트 로드."""
    cur = conn.cursor()
    cur.execute("SELECT exchange, symbol FROM coin_listing WHERE is_active = TRUE")
    known = {(row[0], row[1]) for row in cur.fetchall()}
    cur.close()
    return known


def main():
    logger.info(f"Listing Monitor 시작 (poll={POLL_INTERVAL}s, bootstrap={BOOTSTRAP_MODE})")
    conn = connect_db()
    known_markets = load_known_markets(conn)
    logger.info(f"기존 종목 로드: {len(known_markets)}개")

    is_first_run = True

    while True:
        try:
            # 연결 상태 확인
            try:
                conn.isolation_level
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.close()
            except Exception:
                logger.warning("DB 연결 끊김, 재연결 시도")
                try:
                    conn.close()
                except Exception:
                    pass
                conn = connect_db()
                known_markets = load_known_markets(conn)

            # API 호출
            current_coins = []
            try:
                current_coins.extend(fetch_upbit())
            except Exception as e:
                logger.error(f"업비트 API 오류: {e}")
            try:
                current_coins.extend(fetch_bithumb())
            except Exception as e:
                logger.error(f"빗썸 API 오류: {e}")

            if not current_coins:
                logger.warning("API에서 종목을 가져오지 못함, 다음 폴링 대기")
                time.sleep(POLL_INTERVAL)
                continue

            current_set = {(c["exchange"], c["symbol"]) for c in current_coins}
            new_keys = current_set - known_markets

            if new_keys:
                skip_notify = BOOTSTRAP_MODE and is_first_run
                new_coins = [c for c in current_coins if (c["exchange"], c["symbol"]) in new_keys]
                cur = conn.cursor()

                for coin in new_coins:
                    # coin_listing UPSERT
                    cur.execute(UPSERT_SQL, (
                        coin["exchange"], coin["symbol"], coin["market_code"],
                        coin["korean_name"], coin["english_name"],
                    ))
                    # listing_event INSERT
                    notified = not skip_notify
                    cur.execute(INSERT_EVENT_SQL, (
                        coin["exchange"], coin["symbol"], coin["market_code"],
                        coin["korean_name"], coin["english_name"], notified,
                    ))
                    # 텔레그램 알림
                    if not skip_notify:
                        exchange_kr = "업비트" if coin["exchange"] == "upbit" else "빗썸"
                        name_part = ""
                        if coin["korean_name"]:
                            name_part = f" ({coin['korean_name']})"
                        now_kst = datetime.now(KST).strftime("%H:%M:%S KST")
                        msg = (
                            f"🆕 *신규 상장 감지*\n"
                            f"• 거래소: {exchange_kr}\n"
                            f"• 종목: {coin['symbol']}{name_part}\n"
                            f"• 마켓: {coin['market_code']}\n"
                            f"• 시간: {now_kst}"
                        )
                        send_telegram(msg)

                    known_markets.add((coin["exchange"], coin["symbol"]))

                conn.commit()
                cur.close()

                if skip_notify:
                    logger.info(f"부트스트랩: {len(new_coins)}개 종목 추가 (알림 스킵)")
                else:
                    logger.info(f"신규 상장 감지: {len(new_coins)}개")
            else:
                logger.debug("변경 없음")

            is_first_run = False

        except Exception as e:
            logger.error(f"폴링 오류: {e}")
            try:
                conn.rollback()
            except Exception:
                pass

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            logger.error(f"치명적 오류: {e}, 10초 후 재시작")
            time.sleep(10)
