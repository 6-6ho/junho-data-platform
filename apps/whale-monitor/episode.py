"""에피소드 감지 + 프로파일 스냅샷 + 아웃컴 추적 + 자동 라벨링."""
import os
import json
import time
import logging
from datetime import datetime, timezone

from telegram import send_telegram
from matcher import find_similar_episodes

logger = logging.getLogger(__name__)

EPISODE_TRIGGER_PCT = float(os.getenv("EPISODE_TRIGGER_PCT", "1.0"))
COOLDOWN_MINUTES = 20


def detect_episode(conn, state, symbol):
    """15분 내 +-1% 이상 움직임 감지 → 에피소드 생성."""
    prices = state["price_history"]
    if len(prices) < 90:  # 최소 15분 (10초 × 90)
        return

    current_price = prices[-1]["price"]
    price_15m_ago = prices[-90]["price"]
    change_pct = (current_price - price_15m_ago) / price_15m_ago * 100

    if abs(change_pct) < EPISODE_TRIGGER_PCT:
        return

    direction = "up" if change_pct > 0 else "down"

    # 중복 방지: 최근 N분 내 같은 방향 에피소드
    if _recent_episode_exists(conn, symbol, direction, COOLDOWN_MINUTES):
        return

    # 프로파일 스냅샷
    profile = _build_profile(state, symbol, current_price, change_pct, direction)

    # DB 저장
    episode_id = _insert_episode(conn, profile)
    if episode_id is None:
        return

    # 아웃컴 추적 예약
    state["pending_outcomes"].append({
        "episode_id": episode_id,
        "trigger_price": current_price,
        "detected_at": time.time(),
        "checkpoints": {
            300: None,      # 5분
            900: None,      # 15분
            3600: None,     # 1시간
            14400: None,    # 4시간
            86400: None,    # 24시간
        },
        "prices_seen": [current_price],
    })

    # 유사 에피소드 매칭
    similar = find_similar_episodes(conn, profile, limit=10)

    # 매칭 결과 DB에 저장
    if similar:
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE move_episode SET similar_episodes = %s WHERE id = %s",
                (json.dumps(similar), episode_id),
            )
            conn.commit()
            cur.close()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

    # 텔레그램 알림
    _send_episode_alert(profile, similar)

    logger.info(
        f"에피소드 #{episode_id} 감지: {symbol} {direction} {change_pct:+.2f}% "
        f"@ ${current_price:,.0f}"
    )


def track_outcomes(conn, state):
    """보류 중인 에피소드의 아웃컴을 시간에 따라 기록."""
    if not state["price_history"]:
        return

    current_price = state["price_history"][-1]["price"]
    now = time.time()
    completed = []

    for ep in state["pending_outcomes"]:
        ep["prices_seen"].append(current_price)
        elapsed = now - ep["detected_at"]

        for checkpoint_sec in sorted(ep["checkpoints"].keys()):
            if ep["checkpoints"][checkpoint_sec] is not None:
                continue
            if elapsed >= checkpoint_sec:
                ret = (current_price - ep["trigger_price"]) / ep["trigger_price"] * 100
                ep["checkpoints"][checkpoint_sec] = ret
                _update_outcome(conn, ep["episode_id"], checkpoint_sec, ret)

                # 1시간 체크포인트에서 중간 알림
                if checkpoint_sec == 3600:
                    _send_update_alert(ep, ret, current_price)

        # 모든 체크포인트 완료 → 라벨링
        if all(v is not None for v in ep["checkpoints"].values()):
            max_price = max(ep["prices_seen"])
            min_price = min(ep["prices_seen"])
            max_ret = (max_price - ep["trigger_price"]) / ep["trigger_price"] * 100
            max_dd = (min_price - ep["trigger_price"]) / ep["trigger_price"] * 100
            label = _auto_label(ep, max_ret, max_dd)
            _finalize_episode(conn, ep["episode_id"], max_ret, max_dd, label)
            completed.append(ep)
            logger.info(
                f"에피소드 #{ep['episode_id']} 완료: label={label} "
                f"max={max_ret:+.2f}% dd={max_dd:+.2f}%"
            )

    for ep in completed:
        state["pending_outcomes"].remove(ep)


# === 내부 함수 ===


def _recent_episode_exists(conn, symbol, direction, minutes):
    """최근 N분 내 같은 방향 에피소드 존재 여부."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT 1 FROM move_episode
            WHERE symbol = %s AND direction = %s
              AND detected_at > NOW() - INTERVAL '%s minutes'
            LIMIT 1
        """, (symbol, direction, minutes))
        exists = cur.fetchone() is not None
        cur.close()
        return exists
    except Exception as e:
        logger.error(f"중복 체크 오류: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _build_profile(state, symbol, current_price, change_pct, direction):
    """감지 시점의 시장 상태 프로파일 스냅샷."""
    now = time.time()
    window_5m = now - 300

    # 5분 내 청산 집계
    short_liqs = [
        liq for liq in state["liquidations"]
        if liq["ts"] >= window_5m and liq["side"] == "BUY"  # BUY = 숏 청산
        and "BTC" in liq["symbol"]
    ]
    long_liqs = [
        liq for liq in state["liquidations"]
        if liq["ts"] >= window_5m and liq["side"] == "SELL"  # SELL = 롱 청산
        and "BTC" in liq["symbol"]
    ]

    # 5분 내 고래 순매수
    whale_buys = sum(
        t["notional_usd"] for t in state["whale_trades"]
        if t["ts"] >= window_5m and t["side"] == "BUY"
    )
    whale_sells = sum(
        t["notional_usd"] for t in state["whale_trades"]
        if t["ts"] >= window_5m and t["side"] == "SELL"
    )

    # OI 변화율
    oi_change_pct = None
    if state["oi_history"]:
        oi_change_pct = state["oi_history"][-1].get("change_pct")

    # 호가 깊이
    depth = state.get("last_depth", {})

    # 볼륨 서지 (5분 내 고래 거래 수 / 평균)
    recent_whale_count = len([
        t for t in state["whale_trades"] if t["ts"] >= window_5m
    ])
    avg_whale_count = max(len(state["whale_trades"]) / 12, 1)  # 대략 1시간 / 5분
    volume_surge = recent_whale_count / avg_whale_count

    profile = {
        "symbol": symbol,
        "detected_at": datetime.now(timezone.utc),
        "trigger_price": current_price,
        "price_change_pct": change_pct,
        "direction": direction,
        "oi_change_pct": oi_change_pct,
        "short_liq_count": len(short_liqs),
        "short_liq_usd": sum(l["notional_usd"] for l in short_liqs),
        "long_liq_count": len(long_liqs),
        "long_liq_usd": sum(l["notional_usd"] for l in long_liqs),
        "depth_imbalance": depth.get("depth_imbalance"),
        "bid_depth_1pct": depth.get("bid_depth_1pct"),
        "ask_depth_1pct": depth.get("ask_depth_1pct"),
        "funding_rate": state.get("last_funding"),
        "funding_rate_delta": state.get("last_funding_delta"),
        "whale_net_buy_usd": whale_buys - whale_sells,
        "ls_ratio": state.get("last_ls_ratio"),
        "volume_surge_ratio": volume_surge,
    }
    return profile


def _insert_episode(conn, profile):
    """에피소드 DB 삽입, id 반환."""
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO move_episode
                (symbol, detected_at, trigger_price, price_change_pct, direction,
                 oi_change_pct, short_liq_count, short_liq_usd,
                 long_liq_count, long_liq_usd,
                 depth_imbalance, bid_depth_1pct, ask_depth_1pct,
                 funding_rate, funding_rate_delta,
                 whale_net_buy_usd, ls_ratio, volume_surge_ratio,
                 profile_json)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            profile["symbol"],
            profile["detected_at"],
            profile["trigger_price"],
            profile["price_change_pct"],
            profile["direction"],
            profile["oi_change_pct"],
            profile["short_liq_count"],
            profile["short_liq_usd"],
            profile["long_liq_count"],
            profile["long_liq_usd"],
            profile["depth_imbalance"],
            profile["bid_depth_1pct"],
            profile["ask_depth_1pct"],
            profile["funding_rate"],
            profile["funding_rate_delta"],
            profile["whale_net_buy_usd"],
            profile["ls_ratio"],
            profile["volume_surge_ratio"],
            json.dumps({
                k: (v.isoformat() if isinstance(v, datetime) else v)
                for k, v in profile.items()
            }),
        ))
        episode_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return episode_id
    except Exception as e:
        logger.error(f"에피소드 저장 오류: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return None


def _update_outcome(conn, episode_id, checkpoint_sec, ret):
    """개별 아웃컴 체크포인트 업데이트."""
    col_map = {
        300: "return_5m",
        900: "return_15m",
        3600: "return_1h",
        14400: "return_4h",
        86400: "return_24h",
    }
    col = col_map.get(checkpoint_sec)
    if not col:
        return

    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE move_episode SET {col} = %s WHERE id = %s",
            (ret, episode_id),
        )
        conn.commit()
        cur.close()
        logger.debug(f"에피소드 #{episode_id} {col}={ret:+.2f}%")
    except Exception as e:
        logger.error(f"아웃컴 업데이트 오류: {e}")
        try:
            conn.rollback()
        except Exception:
            pass


def _finalize_episode(conn, episode_id, max_ret, max_dd, label):
    """에피소드 최종 라벨링."""
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE move_episode
            SET max_return = %s, max_drawdown = %s, label = %s
            WHERE id = %s
        """, (max_ret, max_dd, label, episode_id))
        conn.commit()
        cur.close()
    except Exception as e:
        logger.error(f"에피소드 완료 오류: {e}")
        try:
            conn.rollback()
        except Exception:
            pass


def _auto_label(ep, max_ret, max_dd):
    """아웃컴 기반 자동 라벨링.

    조건:
    - squeeze_reversal: 15m 내 상승분 50%+ 되돌림
    - squeeze_continuation: 초기 OI↓ → 1h 유지
    - genuine_rally: OI↑ + 1h 후에도 상승 유지
    - genuine_sustained: 4h+ 상승 유지
    - fakeout: 1h 내 전량 되돌림
    """
    ret_5m = ep["checkpoints"].get(300, 0) or 0
    ret_15m = ep["checkpoints"].get(900, 0) or 0
    ret_1h = ep["checkpoints"].get(3600, 0) or 0
    ret_4h = ep["checkpoints"].get(14400, 0) or 0

    # 상승 에피소드 기준 (하락은 부호 반전)
    # fakeout: 1h 내 전량 되돌림
    if abs(ret_1h) < 0.2:
        return "fakeout"

    # squeeze_reversal: 15분 내 50%+ 되돌림
    if ret_5m > 0 and ret_15m < ret_5m * 0.5:
        return "squeeze_reversal"
    if ret_5m < 0 and ret_15m > ret_5m * 0.5:
        return "squeeze_reversal"

    # genuine_sustained: 4h+ 같은 방향 유지
    if ret_5m > 0 and ret_4h > ret_5m * 0.5:
        return "genuine_sustained"
    if ret_5m < 0 and ret_4h < ret_5m * 0.5:
        return "genuine_sustained"

    # squeeze_continuation / genuine_rally
    if ret_1h > 0 and ret_5m > 0:
        return "genuine_rally"
    if ret_1h < 0 and ret_5m < 0:
        return "genuine_rally"

    return "squeeze_continuation"


def _send_episode_alert(profile, similar):
    """에피소드 감지 텔레그램 알림."""
    p = profile
    direction_str = "상승" if p["direction"] == "up" else "하락"

    lines = [
        f"*가격 에피소드 감지 — BTC*",
        "",
        f"• 움직임: {p['price_change_pct']:+.1f}% (15분) {direction_str}",
        f"• 가격: ${p['trigger_price']:,.0f}",
        "",
        "*프로파일:*",
    ]

    if p["oi_change_pct"] is not None:
        oi_desc = "숏 청산 중" if p["oi_change_pct"] < 0 else "신규 유입"
        lines.append(f"• OI: {p['oi_change_pct']:+.1f}% ({oi_desc})")

    if p["short_liq_count"] > 0:
        lines.append(
            f"• 숏 청산: {p['short_liq_count']}건 / ${p['short_liq_usd']:,.0f}"
        )
    if p["long_liq_count"] > 0:
        lines.append(
            f"• 롱 청산: {p['long_liq_count']}건 / ${p['long_liq_usd']:,.0f}"
        )

    if p["bid_depth_1pct"] and p["ask_depth_1pct"]:
        bid_m = p["bid_depth_1pct"] / 1_000_000
        ask_m = p["ask_depth_1pct"] / 1_000_000
        imb = (p["depth_imbalance"] or 0) * 100
        lines.append(
            f"• 호가: 매수 ${bid_m:.0f}M vs 매도 ${ask_m:.0f}M ({imb:+.0f}%)"
        )

    if p["whale_net_buy_usd"]:
        lines.append(f"• 고래: 순매수 ${p['whale_net_buy_usd']:,.0f}")

    if p["funding_rate"] is not None:
        delta_str = ""
        if p["funding_rate_delta"] is not None:
            delta_str = f" (변화 {p['funding_rate_delta']:+.4f})"
        lines.append(f"• 펀딩비: {p['funding_rate']:.4f}%{delta_str}")

    # 유사 에피소드
    if similar and similar.get("count", 0) > 0:
        lines.append("")
        lines.append(f"*유사 에피소드 {similar['count']}건:*")
        for label, count in similar.get("label_distribution", {}).items():
            pct = count / similar["count"] * 100
            avg_1h = similar.get("avg_by_label", {}).get(label, {}).get("avg_return_1h", 0)
            lines.append(f"• {label} {pct:.0f}% → 1h 평균 {avg_1h:+.1f}%")

    send_telegram("\n".join(lines))


def _send_update_alert(ep, ret_1h, current_price):
    """1시간 체크포인트 업데이트 알림."""
    max_p = max(ep["prices_seen"])
    min_p = min(ep["prices_seen"])
    max_ret = (max_p - ep["trigger_price"]) / ep["trigger_price"] * 100
    min_ret = (min_p - ep["trigger_price"]) / ep["trigger_price"] * 100
    cur_ret = (current_price - ep["trigger_price"]) / ep["trigger_price"] * 100

    msg = (
        f"*에피소드 업데이트 — BTC* (#{ep['episode_id']})\n"
        f"\n"
        f"• 1시간 경과: {ret_1h:+.1f}%\n"
        f"• max: {max_ret:+.1f}% / min: {min_ret:+.1f}%\n"
        f"• 현재: {cur_ret:+.1f}% (${current_price:,.0f})"
    )
    send_telegram(msg)
