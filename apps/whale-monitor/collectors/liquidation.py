"""청산 이벤트 수집기 — WebSocket 실시간."""
import json
import time
import logging
from datetime import datetime, timezone

import websocket

logger = logging.getLogger(__name__)

WS_URL = "wss://fstream.binance.com/ws/!forceOrder@arr"


def run_liquidation_ws(conn, state):
    """forceOrder WebSocket → 청산 이벤트 저장 + 메모리 링버퍼."""
    while True:
        try:
            ws = websocket.WebSocketApp(
                WS_URL,
                on_open=lambda ws: logger.info("청산 WS 연결됨"),
                on_message=lambda ws, msg: _on_liq_message(conn, state, msg),
                on_error=lambda ws, err: logger.error(f"청산 WS 오류: {err}"),
                on_close=lambda ws, code, msg: logger.info("청산 WS 닫힘"),
            )
            ws.run_forever(ping_interval=30, ping_timeout=10)
            time.sleep(5)
        except Exception as e:
            logger.error(f"청산 WS 루프 오류: {e}")
            time.sleep(5)


def _on_liq_message(conn, state, raw_msg):
    """개별 청산 이벤트 처리."""
    try:
        data = json.loads(raw_msg)
        # forceOrder 형식: {"e":"forceOrder","E":...,"o":{...}}
        order = data.get("o", data)

        symbol = order.get("s", "")
        side = order.get("S", "")  # BUY = 숏 청산, SELL = 롱 청산
        price = float(order.get("p", 0))
        qty = float(order.get("q", 0))
        notional = price * qty
        event_time_ms = order.get("T", data.get("E", int(time.time() * 1000)))
        event_time = datetime.fromtimestamp(event_time_ms / 1000, tz=timezone.utc)

        # 링버퍼에 추가
        state["liquidations"].append({
            "symbol": symbol,
            "side": side,
            "price": price,
            "quantity": qty,
            "notional_usd": notional,
            "event_time": event_time,
            "ts": time.time(),
        })

        # BTCUSDT만 DB 저장 (주요 심볼)
        if "BTCUSDT" in symbol:
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO liquidation_event
                        (symbol, side, price, quantity, notional_usd, event_time)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (symbol, side, price, qty, notional, event_time))
                conn.commit()
                cur.close()
            except Exception as e:
                logger.error(f"청산 DB 저장 오류: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass

    except Exception as e:
        logger.error(f"청산 메시지 처리 오류: {e}")
