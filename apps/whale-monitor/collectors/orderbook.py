"""호가 깊이 수집기 — 30초 폴링, 1%/5% 범위 집계."""
import logging
import requests

logger = logging.getLogger(__name__)

DEPTH_URL = "https://fapi.binance.com/fapi/v1/depth"


def collect_orderbook_depth(conn, state, symbol):
    """Binance depth API → 1%/5% 범위 매수/매도벽 크기 + 불균형 계산."""
    try:
        resp = requests.get(DEPTH_URL, params={"symbol": symbol, "limit": 1000}, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        bids = [(float(p), float(q)) for p, q in data["bids"]]
        asks = [(float(p), float(q)) for p, q in data["asks"]]

        if not bids or not asks:
            return

        best_bid = bids[0][0]
        best_ask = asks[0][0]
        mid_price = (best_bid + best_ask) / 2

        # 1% / 5% 범위 내 depth 합산 (USD 기준)
        bid_1pct = sum(p * q for p, q in bids if p >= mid_price * 0.99)
        ask_1pct = sum(p * q for p, q in asks if p <= mid_price * 1.01)
        bid_5pct = sum(p * q for p, q in bids if p >= mid_price * 0.95)
        ask_5pct = sum(p * q for p, q in asks if p <= mid_price * 1.05)

        # depth imbalance: -1 (매도 우세) ~ +1 (매수 우세)
        total_1pct = bid_1pct + ask_1pct
        imbalance = (bid_1pct - ask_1pct) / total_1pct if total_1pct > 0 else 0

        # state 업데이트
        state["last_depth"] = {
            "mid_price": mid_price,
            "bid_depth_1pct": bid_1pct,
            "ask_depth_1pct": ask_1pct,
            "bid_depth_5pct": bid_5pct,
            "ask_depth_5pct": ask_5pct,
            "depth_imbalance": imbalance,
        }

        # DB 저장
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO orderbook_depth
                (symbol, mid_price, bid_depth_1pct, ask_depth_1pct,
                 bid_depth_5pct, ask_depth_5pct, depth_imbalance)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (symbol, mid_price, bid_1pct, ask_1pct, bid_5pct, ask_5pct, imbalance))
        conn.commit()
        cur.close()

        logger.debug(f"호가 깊이 수집: mid={mid_price:.1f} imbalance={imbalance:+.3f}")

    except Exception as e:
        logger.error(f"호가 깊이 수집 오류: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
