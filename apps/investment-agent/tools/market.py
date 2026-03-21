"""시장 데이터 조회 + 스크리닝."""
import json
from decimal import Decimal
from db import execute_query


def _serialize(obj):
    """JSON 직렬화 헬퍼."""
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def get_market_summary() -> str:
    """현재 시장 상태 요약 — movers + whale 에피소드 + 호가."""
    # 최근 movers (변동률 상위)
    movers = execute_query("""
        SELECT DISTINCT ON (symbol)
            symbol, change_pct_window, change_pct_24h, vol_ratio, "window", event_time
        FROM movers_latest
        WHERE type = 'rise'
        ORDER BY symbol, event_time DESC
        LIMIT 10
    """)

    # 최근 whale 에피소드
    episodes = execute_query("""
        SELECT symbol, detected_at, trigger_price, price_change_pct, direction,
               label, return_1h, max_return
        FROM move_episode
        ORDER BY detected_at DESC
        LIMIT 5
    """)

    # 최근 호가 깊이
    depth = execute_query("""
        SELECT mid_price, depth_imbalance, bid_depth_1pct, ask_depth_1pct
        FROM orderbook_depth
        WHERE symbol = 'BTCUSDT'
        ORDER BY recorded_at DESC
        LIMIT 1
    """)

    return json.dumps({
        "top_movers": movers,
        "recent_episodes": episodes,
        "btc_depth": depth[0] if depth else None,
    }, default=_serialize, ensure_ascii=False)


def screen_coins(criteria_name: str | None = None) -> str:
    """종목 스크리닝 — 기존 screener + movers 데이터 활용.

    criteria_name이 있으면 해당 기준의 content를 참조용으로 반환.
    실제 필터링은 기본 조건: 거래량 상위 + 최근 변동.
    """
    # 기준 조회 (참조용)
    criteria_content = None
    if criteria_name:
        rows = execute_query(
            "SELECT content FROM investment_criteria WHERE name = %s",
            (criteria_name,),
        )
        if rows:
            criteria_content = rows[0]["content"]

    # 스크리너: junk이 아닌 종목 중 거래량 상위
    screener = execute_query("""
        SELECT exchange, symbol, price_krw, market_cap_krw, volume_24h_krw,
               junk_score, is_low_cap, is_long_decline
        FROM coin_screener_latest
        WHERE junk_score = 0
        ORDER BY volume_24h_krw DESC NULLS LAST
        LIMIT 20
    """)

    # 최근 movers (5분/2시간 윈도우 변동)
    movers = execute_query("""
        SELECT DISTINCT ON (symbol)
            symbol, change_pct_window, change_pct_24h, vol_ratio, "window"
        FROM movers_latest
        WHERE type = 'rise' AND event_time > NOW() - INTERVAL '1 hour'
        ORDER BY symbol, event_time DESC
    """)

    # movers 심볼 매핑
    mover_map = {m["symbol"]: m for m in movers}

    # 결합
    results = []
    for coin in screener:
        symbol = coin["symbol"]
        mover = mover_map.get(symbol)
        results.append({
            **coin,
            "recent_move": mover if mover else None,
            "is_moving": mover is not None,
        })

    # 움직이는 종목 우선
    results.sort(key=lambda x: (not x["is_moving"], -(x.get("volume_24h_krw") or 0)))

    return json.dumps({
        "criteria_applied": criteria_name,
        "criteria_content": criteria_content,
        "coins": results[:20],
        "total_screened": len(screener),
        "currently_moving": sum(1 for r in results if r["is_moving"]),
    }, default=_serialize, ensure_ascii=False)


def get_coin_detail(symbol: str) -> str:
    """특정 코인 상세 — 가격, 변동, 스크리너 정보."""
    # market_snapshot
    market = execute_query("""
        SELECT symbol, price, change_pct_24h, volume_24h, updated_at
        FROM market_snapshot WHERE symbol = %s
    """, (symbol,))

    # screener
    screener = execute_query("""
        SELECT exchange, price_krw, market_cap_krw, volume_24h_krw,
               junk_score, is_low_cap, is_long_decline, is_no_pump
        FROM coin_screener_latest WHERE symbol = %s
    """, (symbol,))

    # 최근 movers 이벤트
    movers = execute_query("""
        SELECT type, "window", change_pct_window, change_pct_24h, vol_ratio, event_time
        FROM movers_latest
        WHERE symbol = %s
        ORDER BY event_time DESC
        LIMIT 5
    """, (symbol,))

    return json.dumps({
        "symbol": symbol,
        "market": market[0] if market else None,
        "screener": screener,
        "recent_movers": movers,
    }, default=_serialize, ensure_ascii=False)
