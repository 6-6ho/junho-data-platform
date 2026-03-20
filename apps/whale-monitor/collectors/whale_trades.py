"""대형 체결 수집기 — WebSocket 실시간, $100K+ 필터."""
import os
import json
import time
import logging
from datetime import datetime, timezone

import websocket

logger = logging.getLogger(__name__)

WHALE_THRESHOLD = float(os.getenv("WHALE_TRADE_THRESHOLD", "100000"))
WS_URL = "wss://fstream.binance.com/ws/btcusdt@aggTrade"


def run_whale_trade_ws(conn, state):
    """aggTrade WebSocket → $100K+ 필터 → 저장 + 링버퍼."""
    while True:
        try:
            ws = websocket.WebSocketApp(
                WS_URL,
                on_open=lambda ws: logger.info("고래 체결 WS 연결됨"),
                on_message=lambda ws, msg: _on_trade_message(conn, state, msg),
                on_error=lambda ws, err: logger.error(f"고래 체결 WS 오류: {err}"),
                on_close=lambda ws, code, msg: logger.info("고래 체결 WS 닫힘"),
            )
            ws.run_forever(ping_interval=60, ping_timeout=30)
            time.sleep(5)
        except Exception as e:
            logger.error(f"고래 체결 WS 루프 오류: {e}")
            time.sleep(5)


def _on_trade_message(conn, state, raw_msg):
    """aggTrade 처리 — $100K+ 필터."""
    try:
        data = json.loads(raw_msg)

        price = float(data["p"])
        qty = float(data["q"])
        notional = price * qty

        if notional < WHALE_THRESHOLD:
            return

        # m = true → 매도자가 maker → 매수 체결 (taker buy)
        side = "SELL" if data.get("m", False) else "BUY"
        trade_time = datetime.fromtimestamp(data["T"] / 1000, tz=timezone.utc)

        # 링버퍼
        state["whale_trades"].append({
            "symbol": "BTCUSDT",
            "side": side,
            "price": price,
            "quantity": qty,
            "notional_usd": notional,
            "trade_time": trade_time,
            "ts": time.time(),
        })

        # DB 저장
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO whale_trade
                    (symbol, side, price, quantity, notional_usd, trade_time)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, ("BTCUSDT", side, price, qty, notional, trade_time))
            conn.commit()
            cur.close()
        except Exception as e:
            logger.error(f"고래 체결 DB 저장 오류: {e}")
            try:
                conn.rollback()
            except Exception:
                pass

    except Exception as e:
        logger.error(f"고래 체결 메시지 처리 오류: {e}")
