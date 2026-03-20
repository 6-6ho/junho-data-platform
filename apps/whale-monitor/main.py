"""
Whale Monitor — 에피소드 축적형 가격 움직임 분석 시스템.
BTC 대형 움직임 감지 → 프로파일 스냅샷 → 아웃컴 추적 → 유사 에피소드 매칭.
"""
import os
import time
import logging
import threading
from collections import deque

import requests

from db import connect_db, ensure_conn
from collectors.orderbook import collect_orderbook_depth
from collectors.liquidation import run_liquidation_ws
from collectors.whale_trades import run_whale_trade_ws
from collectors.derivatives import collect_derivatives
from collectors.onchain import collect_onchain
from episode import detect_episode, track_outcomes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

PRICE_URL = "https://fapi.binance.com/fapi/v1/ticker/price"
SYMBOL = os.getenv("SYMBOL", "BTCUSDT")


def collect_price(state, symbol):
    """현재 가격 수집 (10초 간격)."""
    try:
        resp = requests.get(PRICE_URL, params={"symbol": symbol}, timeout=5)
        resp.raise_for_status()
        price = float(resp.json()["price"])
        state["price_history"].append({"price": price, "ts": time.time()})
    except Exception as e:
        logger.error(f"가격 수집 오류: {e}")


def cleanup_old_data(conn):
    """오래된 원시 데이터 정리."""
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM orderbook_depth WHERE recorded_at < NOW() - INTERVAL '7 days'")
        cur.execute("DELETE FROM whale_trade WHERE recorded_at < NOW() - INTERVAL '30 days'")
        cur.execute("DELETE FROM liquidation_event WHERE recorded_at < NOW() - INTERVAL '30 days'")
        cur.execute("DELETE FROM whale_transfer WHERE recorded_at < NOW() - INTERVAL '90 days'")
        conn.commit()
        cur.close()
        logger.info("오래된 데이터 정리 완료")
    except Exception as e:
        logger.error(f"데이터 정리 오류: {e}")
        try:
            conn.rollback()
        except Exception:
            pass


def main():
    logger.info(f"Whale Monitor 시작 (symbol={SYMBOL})")
    conn = connect_db()

    # 메모리 링버퍼
    state = {
        "liquidations": deque(maxlen=1000),
        "whale_trades": deque(maxlen=500),
        "price_history": deque(maxlen=600),   # 10초 × 600 = 100분
        "oi_history": deque(maxlen=60),        # 1분 × 60 = 1시간
        "last_depth": {},
        "last_funding": None,
        "last_funding_delta": None,
        "last_ls_ratio": None,
        "pending_outcomes": [],
    }

    # WS 전용 DB 연결 (스레드별 별도 연결)
    ws_conn_liq = connect_db()
    ws_conn_whale = connect_db()

    # WebSocket 스레드
    threading.Thread(
        target=run_liquidation_ws, args=(ws_conn_liq, state), daemon=True
    ).start()
    threading.Thread(
        target=run_whale_trade_ws, args=(ws_conn_whale, state), daemon=True
    ).start()

    logger.info("WebSocket 스레드 시작됨")

    # 타이머
    last_depth = 0
    last_deriv = 0
    last_onchain = 0
    last_episode_check = 0
    last_outcome_check = 0
    last_cleanup = 0

    while True:
        now = time.time()

        # DB 연결 확인
        conn = ensure_conn(conn)

        # 가격 수집 (매 루프 = ~5초)
        collect_price(state, SYMBOL)

        # 호가 깊이 (30초)
        if now - last_depth >= 30:
            collect_orderbook_depth(conn, state, SYMBOL)
            last_depth = now

        # 파생상품 (1분)
        if now - last_deriv >= 60:
            collect_derivatives(conn, state, SYMBOL)
            last_deriv = now

        # 온체인 (1분)
        if now - last_onchain >= 60:
            collect_onchain(conn)
            last_onchain = now

        # 에피소드 감지 (10초)
        if now - last_episode_check >= 10:
            detect_episode(conn, state, SYMBOL)
            last_episode_check = now

        # 아웃컴 추적 (30초)
        if now - last_outcome_check >= 30:
            track_outcomes(conn, state)
            last_outcome_check = now

        # 데이터 정리 (1일)
        if now - last_cleanup >= 86400:
            cleanup_old_data(conn)
            last_cleanup = now

        time.sleep(5)


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            logger.error(f"치명적 오류: {e}, 10초 후 재시작")
            time.sleep(10)
