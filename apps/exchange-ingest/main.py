"""
Multi-Exchange Price Collector

Upbit WebSocket + Bithumb REST → exchange_price_snapshot 테이블.
Binance market_snapshot과 교차검증하여 거래소 간 가격 괴리 감지.

교차검증 로직:
  - Binance USDT 가격 × USDT/KRW 환율 vs Upbit/Bithumb KRW 가격
  - 괴리율 1% 이상 → dq_trade_anomaly_log에 기록
"""
import os
import json
import time
import threading
import logging
from datetime import datetime

import websocket
import requests
import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "app")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")

# USDT/KRW 환율 (교차검증용)
USDT_KRW_RATE = 1380.0  # 초기값, 주기적 업데이트

# Binance에도 있는 주요 코인만 추적 (coin_listing.on_binance = TRUE 기반)
TOP_SYMBOLS = []


def get_conn():
    return psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS)


def load_tracked_symbols():
    """coin_listing에서 Binance에도 상장된 코인 목록 로드."""
    global TOP_SYMBOLS
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT symbol FROM coin_listing
            WHERE on_binance = TRUE AND is_active = TRUE
            ORDER BY symbol LIMIT 100
        """)
        TOP_SYMBOLS = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
        logger.info(f"Loaded {len(TOP_SYMBOLS)} tracked symbols")
    except Exception as e:
        logger.warning(f"Failed to load symbols: {e}, using defaults")
        TOP_SYMBOLS = ["BTC", "ETH", "XRP", "SOL", "DOGE", "ADA", "AVAX", "DOT", "MATIC", "LINK"]


def update_usdt_krw():
    """USDT/KRW 환율 업데이트 (Upbit API)."""
    global USDT_KRW_RATE
    try:
        resp = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-USDT", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                USDT_KRW_RATE = float(data[0]["trade_price"])
                logger.info(f"USDT/KRW rate updated: {USDT_KRW_RATE}")
    except Exception as e:
        logger.warning(f"USDT/KRW update failed: {e}")


def upsert_prices(exchange, prices):
    """exchange_price_snapshot에 가격 upsert."""
    if not prices:
        return
    try:
        conn = get_conn()
        cur = conn.cursor()
        execute_values(cur, """
            INSERT INTO exchange_price_snapshot (exchange, symbol, price_krw, volume_24h)
            VALUES %s
            ON CONFLICT (exchange, symbol) DO UPDATE SET
                price_krw = EXCLUDED.price_krw,
                volume_24h = EXCLUDED.volume_24h,
                updated_at = NOW()
        """, [(exchange, p["symbol"], p["price_krw"], p.get("volume", 0)) for p in prices])
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"[{exchange}] DB upsert failed: {e}")


def check_cross_exchange():
    """Binance vs Upbit/Bithumb 가격 교차검증."""
    try:
        conn = get_conn()
        cur = conn.cursor()

        # Binance 가격 (USDT → KRW 변환)
        cur.execute("""
            SELECT ms.symbol,
                   ms.price * %s as binance_krw,
                   up.price_krw as upbit_krw,
                   bt.price_krw as bithumb_krw
            FROM market_snapshot ms
            LEFT JOIN exchange_price_snapshot up
                ON REPLACE(ms.symbol, 'USDT', '') = up.symbol AND up.exchange = 'upbit'
            LEFT JOIN exchange_price_snapshot bt
                ON REPLACE(ms.symbol, 'USDT', '') = bt.symbol AND bt.exchange = 'bithumb'
            WHERE (up.price_krw IS NOT NULL OR bt.price_krw IS NOT NULL)
              AND ms.price > 0
        """, (USDT_KRW_RATE,))

        divergent = []
        for row in cur.fetchall():
            symbol, binance_krw, upbit_krw, bithumb_krw = row
            for exch, krw_price in [("upbit", upbit_krw), ("bithumb", bithumb_krw)]:
                if krw_price and krw_price > 0 and binance_krw > 0:
                    div = abs(binance_krw - krw_price) / binance_krw * 100
                    if div > 3.0:  # 3% 이상 괴리
                        divergent.append((symbol, exch, binance_krw, krw_price, div))

        # 심각한 괴리 → anomaly log
        for symbol, exch, binance_krw, exch_krw, div in divergent:
            cur.execute("""
                INSERT INTO dq_trade_anomaly_log
                (anomaly_type, dimension, expected_value, actual_value, severity, notes)
                VALUES ('price_divergence', %s, %s, %s, %s, %s)
            """, (f"{exch}:{symbol}", binance_krw, exch_krw,
                  'critical' if div > 10 else 'warning',
                  f"Binance≈{binance_krw:.0f}KRW vs {exch}={exch_krw:.0f}KRW, div={div:.1f}%"))

        if divergent:
            conn.commit()
            logger.warning(f"[CrossExchange] {len(divergent)} divergences detected (>3%)")

        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"[CrossExchange] Check failed: {e}")


# === Upbit WebSocket ===

def run_upbit_ws():
    """Upbit WebSocket으로 실시간 가격 수집."""
    codes = [f"KRW-{s}" for s in TOP_SYMBOLS]
    if not codes:
        logger.warning("No symbols to track for Upbit")
        return

    def on_open(ws):
        payload = json.dumps([
            {"ticket": "exchange-ingest"},
            {"type": "ticker", "codes": codes},
        ])
        ws.send(payload)
        logger.info(f"Upbit WS connected, tracking {len(codes)} codes")

    def on_message(ws, message):
        try:
            data = json.loads(message) if isinstance(message, str) else json.loads(message.decode('utf-8'))
            symbol = data.get("code", "").replace("KRW-", "")
            price = float(data.get("trade_price", 0))
            volume = float(data.get("acc_trade_volume_24h", 0))
            if symbol and price > 0:
                upsert_prices("upbit", [{"symbol": symbol, "price_krw": price, "volume": volume}])
        except Exception as e:
            logger.debug(f"Upbit parse error: {e}")

    def on_error(ws, error):
        logger.error(f"Upbit WS error: {error}")

    def on_close(ws, code, msg):
        logger.warning(f"Upbit WS closed: {code} {msg}")

    while True:
        try:
            ws = websocket.WebSocketApp(
                "wss://api.upbit.com/websocket/v1",
                on_open=on_open, on_message=on_message,
                on_error=on_error, on_close=on_close,
            )
            ws.run_forever(ping_interval=30)
        except Exception as e:
            logger.error(f"Upbit WS fatal: {e}")
        logger.info("Upbit WS reconnecting in 5s...")
        time.sleep(5)


# === Bithumb REST Polling ===

def run_bithumb_poll():
    """Bithumb REST API로 주기적 가격 수집 (30초 간격)."""
    while True:
        try:
            resp = requests.get("https://api.bithumb.com/public/ticker/ALL_KRW", timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                prices = []
                for symbol, info in data.items():
                    if symbol in ("date",) or not isinstance(info, dict):
                        continue
                    if symbol.upper() in TOP_SYMBOLS:
                        prices.append({
                            "symbol": symbol.upper(),
                            "price_krw": float(info.get("closing_price", 0)),
                            "volume": float(info.get("units_traded_24H", 0)),
                        })
                upsert_prices("bithumb", prices)
                logger.info(f"Bithumb: updated {len(prices)} prices")
        except Exception as e:
            logger.error(f"Bithumb poll error: {e}")
        time.sleep(30)


# === Main ===

def run_periodic_tasks():
    """환율 업데이트 + 교차검증 (5분 간격)."""
    while True:
        update_usdt_krw()
        check_cross_exchange()
        time.sleep(300)


def main():
    logger.info("Exchange Ingest starting...")

    # 심볼 로드
    for attempt in range(5):
        try:
            load_tracked_symbols()
            break
        except Exception:
            logger.warning(f"DB not ready, retrying ({attempt+1}/5)...")
            time.sleep(10)

    update_usdt_krw()

    # 3개 스레드 실행
    threads = [
        threading.Thread(target=run_upbit_ws, daemon=True, name="upbit-ws"),
        threading.Thread(target=run_bithumb_poll, daemon=True, name="bithumb-poll"),
        threading.Thread(target=run_periodic_tasks, daemon=True, name="periodic"),
    ]
    for t in threads:
        t.start()
        logger.info(f"Started thread: {t.name}")

    # 메인 스레드는 살아있기만
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
