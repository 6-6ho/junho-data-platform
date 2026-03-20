"""온체인 대형 이체 수집기 — Whale Alert API 1분 폴링."""
import os
import time
import logging

import requests

logger = logging.getLogger(__name__)

WHALE_ALERT_API_KEY = os.getenv("WHALE_ALERT_API_KEY", "")
WHALE_ALERT_URL = "https://api.whale-alert.io/v1/transactions"
MIN_USD_VALUE = 1_000_000  # $1M 이상만


def collect_onchain(conn):
    """Whale Alert API → BTC 대형 이체 저장."""
    if not WHALE_ALERT_API_KEY:
        return

    try:
        since = int(time.time()) - 120  # 최근 2분
        resp = requests.get(
            WHALE_ALERT_URL,
            params={
                "api_key": WHALE_ALERT_API_KEY,
                "min_value": MIN_USD_VALUE,
                "start": since,
                "cursor": "",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        transactions = data.get("transactions", [])
        if not transactions:
            return

        cur = conn.cursor()
        for tx in transactions:
            if tx.get("symbol", "").lower() != "btc":
                continue

            from_label = tx.get("from", {}).get("owner", "unknown")
            to_label = tx.get("to", {}).get("owner", "unknown")

            # 방향 분류
            from_type = tx.get("from", {}).get("owner_type", "unknown")
            to_type = tx.get("to", {}).get("owner_type", "unknown")

            if to_type == "exchange":
                direction = "to_exchange"  # 매도 압력
            elif from_type == "exchange":
                direction = "from_exchange"  # 인출 (호재)
            else:
                direction = "other"

            tx_hash = tx.get("hash", "")
            amount = float(tx.get("amount", 0))
            amount_usd = float(tx.get("amount_usd", 0))

            # 중복 방지
            cur.execute(
                "SELECT 1 FROM whale_transfer WHERE tx_hash = %s LIMIT 1",
                (tx_hash,),
            )
            if cur.fetchone():
                continue

            cur.execute("""
                INSERT INTO whale_transfer
                    (chain, tx_hash, amount, amount_usd, from_label, to_label,
                     direction, block_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, to_timestamp(%s))
            """, (
                "bitcoin", tx_hash, amount, amount_usd,
                from_label, to_label, direction,
                tx.get("timestamp", int(time.time())),
            ))

        conn.commit()
        cur.close()
        logger.debug(f"온체인 수집: {len(transactions)}건 처리")

    except Exception as e:
        logger.error(f"온체인 수집 오류: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
