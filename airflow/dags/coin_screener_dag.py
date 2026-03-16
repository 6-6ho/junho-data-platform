"""
Coin Screener DAG — 잡코인 자동 분류
- 일 1회 05:00 UTC (14:00 KST)
- 업비트/빗썸 × 바이낸스 교집합 (~185종목)에서 잡코인 분류
- 분류 기준: 저시총 (<3000억), 장기하락 (12주 중 8주↑ 음봉), 신규상장 무펌핑
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta, date
import requests
import time
import logging

logger = logging.getLogger(__name__)

default_args = {
    "owner": "junho",
    "depends_on_past": False,
    "start_date": datetime(2026, 1, 1),
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# Rate limit: CoinGecko free tier
COINGECKO_DELAY = 6  # seconds between calls (10 req/min safe)
UPBIT_CANDLE_DELAY = 0.12  # ~8 req/sec (limit 10)


def fetch_listings(**context):
    """Task 1: 업비트/빗썸/바이낸스 종목 수집 → coin_listing UPSERT"""
    today = date.today()

    # --- 업비트: KRW 마켓 ---
    upbit_resp = requests.get(
        "https://api.upbit.com/v1/market/all", params={"is_details": "false"}, timeout=10
    )
    upbit_resp.raise_for_status()
    upbit_coins = []
    for m in upbit_resp.json():
        code = m["market"]  # 'KRW-BTC'
        if not code.startswith("KRW-"):
            continue
        symbol = code.split("-")[1]
        upbit_coins.append({
            "exchange": "upbit",
            "symbol": symbol,
            "market_code": code,
            "korean_name": m.get("korean_name"),
            "english_name": m.get("english_name"),
        })
    logger.info(f"Upbit KRW markets: {len(upbit_coins)}")

    # --- 빗썸: 전체 KRW ---
    bithumb_resp = requests.get("https://api.bithumb.com/public/ticker/ALL_KRW", timeout=10)
    bithumb_resp.raise_for_status()
    bithumb_data = bithumb_resp.json().get("data", {})
    bithumb_coins = []
    for sym, info in bithumb_data.items():
        if sym == "date" or not isinstance(info, dict):
            continue
        bithumb_coins.append({
            "exchange": "bithumb",
            "symbol": sym,
            "market_code": f"{sym}_KRW",
            "korean_name": None,
            "english_name": None,
        })
    logger.info(f"Bithumb KRW markets: {len(bithumb_coins)}")

    # --- 바이낸스: USDT 페어 심볼 ---
    binance_resp = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=10)
    binance_resp.raise_for_status()
    binance_symbols = set()
    for t in binance_resp.json():
        s = t["symbol"]
        if s.endswith("USDT"):
            binance_symbols.add(s[: -len("USDT")])
    logger.info(f"Binance USDT pairs: {len(binance_symbols)}")

    # --- DB UPSERT ---
    pg_hook = PostgresHook(postgres_conn_id="postgres_default")
    conn = pg_hook.get_conn()
    cur = conn.cursor()

    upsert_sql = """
        INSERT INTO coin_listing (exchange, symbol, market_code, korean_name, english_name,
                                  first_seen_date, is_active, on_binance, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s, NOW())
        ON CONFLICT (exchange, symbol) DO UPDATE SET
            market_code = EXCLUDED.market_code,
            korean_name = COALESCE(EXCLUDED.korean_name, coin_listing.korean_name),
            english_name = COALESCE(EXCLUDED.english_name, coin_listing.english_name),
            is_active = TRUE,
            on_binance = EXCLUDED.on_binance,
            updated_at = NOW()
    """

    all_coins = upbit_coins + bithumb_coins
    for coin in all_coins:
        on_binance = coin["symbol"] in binance_symbols
        cur.execute(upsert_sql, (
            coin["exchange"],
            coin["symbol"],
            coin["market_code"],
            coin["korean_name"],
            coin["english_name"],
            today,
            on_binance,
        ))

    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Upserted {len(all_coins)} listings, binance overlap checked")


def fetch_and_classify(**context):
    """Task 2: 교집합 종목 시총/주봉 수집 → 분류 → coin_screener_daily INSERT"""
    today = date.today()

    pg_hook = PostgresHook(postgres_conn_id="postgres_default")
    conn = pg_hook.get_conn()
    cur = conn.cursor()

    # 교집합 종목 조회
    cur.execute("""
        SELECT exchange, symbol, market_code, first_seen_date
        FROM coin_listing
        WHERE on_binance = TRUE AND is_active = TRUE
    """)
    listings = cur.fetchall()
    logger.info(f"Binance intersection: {len(listings)} coins")

    if not listings:
        logger.warning("No intersection coins found")
        cur.close()
        conn.close()
        return

    # --- CoinGecko 시총 ---
    # symbol -> market_cap_krw mapping
    market_caps = {}
    for page in range(1, 4):  # 최대 750종목 커버
        try:
            cg_resp = requests.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={
                    "vs_currency": "krw",
                    "order": "market_cap_desc",
                    "per_page": 250,
                    "page": page,
                },
                timeout=15,
            )
            if cg_resp.status_code == 429:
                logger.warning(f"CoinGecko rate limited at page {page}, stopping")
                break
            cg_resp.raise_for_status()
            for coin in cg_resp.json():
                sym = coin.get("symbol", "").upper()
                mc = coin.get("market_cap")
                vol = coin.get("total_volume")
                price = coin.get("current_price")
                if sym and mc:
                    market_caps[sym] = {
                        "market_cap": mc,
                        "volume": vol,
                        "price": price,
                    }
            time.sleep(COINGECKO_DELAY)
        except Exception as e:
            logger.error(f"CoinGecko page {page} error: {e}")
            break

    logger.info(f"CoinGecko market caps fetched: {len(market_caps)} coins")

    # --- 업비트 주봉 (교집합 업비트 종목만) ---
    # symbol -> weekly_down_count
    weekly_downs = {}
    upbit_listings = [l for l in listings if l[0] == "upbit"]
    for _, symbol, market_code, _ in upbit_listings:
        try:
            resp = requests.get(
                "https://api.upbit.com/v1/candles/weeks",
                params={"market": market_code, "count": 12},
                timeout=10,
            )
            if resp.status_code == 429:
                time.sleep(1)
                resp = requests.get(
                    "https://api.upbit.com/v1/candles/weeks",
                    params={"market": market_code, "count": 12},
                    timeout=10,
                )
            resp.raise_for_status()
            candles = resp.json()
            down_count = sum(
                1 for c in candles if c.get("trade_price", 0) < c.get("opening_price", 0)
            )
            weekly_downs[symbol] = down_count
            time.sleep(UPBIT_CANDLE_DELAY)
        except Exception as e:
            logger.warning(f"Upbit weekly candle error for {symbol}: {e}")
            weekly_downs[symbol] = None

    logger.info(f"Upbit weekly candles fetched: {len(weekly_downs)} coins")

    # 빗썸 종목은 업비트 주봉 공유 (같은 심볼이면 동일 데이터)
    # 빗썸-only 종목은 주봉 데이터 없음 → weekly_down_count = NULL

    # --- 바이낸스: 상장일 고가 + ATH (전 종목) ---
    # 무펌핑 = 상장 첫날 최고가를 한 번도 넘긴 적 없는 코인
    # symbol -> {listing_day_high, ath, listing_price}
    binance_price_data = {}
    unique_symbols = list({sym for _, sym, _, _ in listings})
    logger.info(f"Fetching Binance listing data for {len(unique_symbols)} unique symbols")

    for symbol in unique_symbols:
        try:
            # 1) 첫 일봉: 상장일 고가
            resp1 = requests.get(
                "https://api.binance.com/api/v3/klines",
                params={
                    "symbol": f"{symbol}USDT",
                    "interval": "1d",
                    "startTime": 0,
                    "limit": 1,
                },
                timeout=10,
            )
            if resp1.status_code != 200:
                continue
            first_candle = resp1.json()
            if not first_candle:
                continue

            listing_price = float(first_candle[0][1])   # open
            listing_day_high = float(first_candle[0][2])  # high

            # 2) 전체 주봉: ATH 계산 (~19년 커버)
            resp2 = requests.get(
                "https://api.binance.com/api/v3/klines",
                params={
                    "symbol": f"{symbol}USDT",
                    "interval": "1w",
                    "startTime": 0,
                    "limit": 1000,
                },
                timeout=10,
            )
            if resp2.status_code != 200:
                continue
            weekly_klines = resp2.json()
            if not weekly_klines:
                continue

            ath = max(float(k[2]) for k in weekly_klines)  # high

            # 3) 최근 30일봉: 20%+ 상승 여부
            resp3 = requests.get(
                "https://api.binance.com/api/v3/klines",
                params={
                    "symbol": f"{symbol}USDT",
                    "interval": "1d",
                    "limit": 30,
                },
                timeout=10,
            )
            had_pump_20pct = False
            if resp3.status_code == 200 and resp3.json():
                for k in resp3.json():
                    open_p, high_p = float(k[1]), float(k[2])
                    if open_p > 0 and (high_p - open_p) / open_p >= 0.20:
                        had_pump_20pct = True
                        break

            binance_price_data[symbol] = {
                "listing_price": listing_price,
                "listing_day_high": listing_day_high,
                "ath": ath,
                "had_pump_20pct_30d": had_pump_20pct,
            }
            time.sleep(0.05)  # Binance 1200 req/min
        except Exception as e:
            logger.warning(f"Binance klines error for {symbol}: {e}")

    logger.info(f"Binance listing data fetched: {len(binance_price_data)} coins")

    # --- 분류 & INSERT ---
    insert_sql = """
        INSERT INTO coin_screener_daily
            (date, exchange, symbol, price_krw, market_cap_krw, volume_24h_krw,
             weekly_down_count, listing_age_days, max_price_since_listing, listing_price,
             is_low_cap, is_long_decline, is_no_pump, had_pump_20pct_30d, junk_score)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (date, exchange, symbol) DO UPDATE SET
            price_krw = EXCLUDED.price_krw,
            market_cap_krw = EXCLUDED.market_cap_krw,
            volume_24h_krw = EXCLUDED.volume_24h_krw,
            weekly_down_count = EXCLUDED.weekly_down_count,
            listing_age_days = EXCLUDED.listing_age_days,
            max_price_since_listing = EXCLUDED.max_price_since_listing,
            listing_price = EXCLUDED.listing_price,
            is_low_cap = EXCLUDED.is_low_cap,
            is_long_decline = EXCLUDED.is_long_decline,
            is_no_pump = EXCLUDED.is_no_pump,
            had_pump_20pct_30d = EXCLUDED.had_pump_20pct_30d,
            junk_score = EXCLUDED.junk_score
    """

    classified_count = 0
    for exchange, symbol, market_code, first_seen in listings:
        cg = market_caps.get(symbol, {})
        mc = cg.get("market_cap")
        vol = cg.get("volume")
        price = cg.get("price")

        # 주봉 음봉 수 (업비트 데이터 기준, 빗썸은 같은 심볼 공유)
        wd = weekly_downs.get(symbol)

        # 상장일수
        listing_age = (today - first_seen).days if first_seen else None

        # 바이낸스 기반 상장일 고가 / ATH
        bp = binance_price_data.get(symbol, {})
        listing_day_high = bp.get("listing_day_high")
        ath = bp.get("ath")
        listing_price_val = bp.get("listing_price")
        max_price = ath

        # --- 분류 ---
        is_low_cap = bool(mc and mc < 300_000_000_000)  # 3000억원
        is_long_decline = bool(wd is not None and wd >= 8)
        # 무펌핑: ATH가 상장 첫날 고가를 넘긴 적 없음
        is_no_pump = bool(listing_day_high and ath and ath <= listing_day_high)
        had_pump_20pct_30d = bp.get("had_pump_20pct_30d", False)

        junk_score = int(is_low_cap) + int(is_long_decline) + int(is_no_pump)

        cur.execute(insert_sql, (
            today, exchange, symbol, price,
            mc, vol, wd, listing_age,
            max_price, listing_price_val,
            is_low_cap, is_long_decline, is_no_pump, had_pump_20pct_30d, junk_score,
        ))
        if junk_score > 0:
            classified_count += 1

    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Classified {classified_count} junk coins out of {len(listings)} total")


def update_latest(**context):
    """Task 3: 당일 coin_screener_daily → coin_screener_latest UPSERT"""
    today = date.today()

    pg_hook = PostgresHook(postgres_conn_id="postgres_default")
    conn = pg_hook.get_conn()
    cur = conn.cursor()

    # 양쪽 거래소 상장 시 업비트 우선 (exchange 정렬 → upbit > bithumb)
    cur.execute("""
        INSERT INTO coin_screener_latest
            (exchange, symbol, price_krw, market_cap_krw, volume_24h_krw,
             weekly_down_count, listing_age_days, max_price_since_listing, listing_price,
             is_low_cap, is_long_decline, is_no_pump, had_pump_20pct_30d, junk_score, updated_at)
        SELECT DISTINCT ON (symbol)
            exchange, symbol, price_krw, market_cap_krw, volume_24h_krw,
            weekly_down_count, listing_age_days, max_price_since_listing, listing_price,
            is_low_cap, is_long_decline, is_no_pump, had_pump_20pct_30d, junk_score, NOW()
        FROM coin_screener_daily
        WHERE date = %s
        ORDER BY symbol, exchange DESC
        ON CONFLICT (exchange, symbol) DO UPDATE SET
            price_krw = EXCLUDED.price_krw,
            market_cap_krw = EXCLUDED.market_cap_krw,
            volume_24h_krw = EXCLUDED.volume_24h_krw,
            weekly_down_count = EXCLUDED.weekly_down_count,
            listing_age_days = EXCLUDED.listing_age_days,
            max_price_since_listing = EXCLUDED.max_price_since_listing,
            listing_price = EXCLUDED.listing_price,
            is_low_cap = EXCLUDED.is_low_cap,
            is_long_decline = EXCLUDED.is_long_decline,
            is_no_pump = EXCLUDED.is_no_pump,
            had_pump_20pct_30d = EXCLUDED.had_pump_20pct_30d,
            junk_score = EXCLUDED.junk_score,
            updated_at = NOW()
    """, (today,))

    conn.commit()

    # 결과 로깅
    cur.execute("""
        SELECT COUNT(*),
               COUNT(*) FILTER (WHERE junk_score > 0),
               COUNT(*) FILTER (WHERE junk_score >= 2)
        FROM coin_screener_latest
    """)
    total, junk, high_junk = cur.fetchone()
    logger.info(f"Latest updated: {total} total, {junk} junk (score>0), {high_junk} high-risk (score>=2)")

    cur.close()
    conn.close()


with DAG(
    "coin_screener",
    default_args=default_args,
    description="잡코인 스크리너: 업비트/빗썸 × 바이낸스 교집합 분류",
    schedule_interval="0 5 * * *",  # 05:00 UTC = 14:00 KST
    catchup=False,
    tags=["trade", "screener"],
) as dag:

    t_fetch_listings = PythonOperator(
        task_id="fetch_listings",
        python_callable=fetch_listings,
    )

    t_fetch_and_classify = PythonOperator(
        task_id="fetch_and_classify",
        python_callable=fetch_and_classify,
    )

    t_update_latest = PythonOperator(
        task_id="update_latest",
        python_callable=update_latest,
    )

    t_fetch_listings >> t_fetch_and_classify >> t_update_latest
