"""유사 에피소드 매칭 — 프로파일 기반 가중 유사도 검색."""
import logging
import statistics

logger = logging.getLogger(__name__)

# 유사도 가중치
WEIGHTS = {
    "oi_change_pct": 30,
    "short_liq_usd": 25,
    "depth_imbalance": 15,
    "whale_net_buy_usd": 20,
    "funding_rate_delta": 10,
}


def find_similar_episodes(conn, profile, limit=10):
    """현재 프로파일과 유사한 과거 에피소드를 찾아서 아웃컴 통계 반환.

    유사도: 주요 필드별 정규화된 거리의 가중합.
    완료된 에피소드만 (24h 아웃컴까지 있는 것).
    """
    completed = _fetch_completed_episodes(conn, profile["symbol"])

    if len(completed) < 5:
        return None

    # 각 필드의 분포 통계 (정규화용)
    field_stats = {}
    for field in WEIGHTS:
        values = [
            ep[field] for ep in completed
            if ep.get(field) is not None
        ]
        if values and len(values) > 1:
            field_stats[field] = {
                "mean": statistics.mean(values),
                "std": statistics.stdev(values),
            }

    # 유사도 계산
    scored = []
    for ep in completed:
        distance = 0
        total_weight = 0

        for field, weight in WEIGHTS.items():
            current_val = profile.get(field)
            ep_val = ep.get(field)

            if current_val is None or ep_val is None:
                continue
            if field not in field_stats or field_stats[field]["std"] == 0:
                continue

            std = field_stats[field]["std"]
            norm_dist = abs(current_val - ep_val) / std
            distance += norm_dist * weight
            total_weight += weight

        if total_weight > 0:
            distance /= total_weight

        scored.append((distance, ep))

    scored.sort(key=lambda x: x[0])
    similar = [ep for _, ep in scored[:limit]]

    if not similar:
        return None

    # 아웃컴 통계 집계
    result = {
        "count": len(similar),
        "avg_return_5m": _safe_avg([e.get("return_5m") for e in similar]),
        "avg_return_15m": _safe_avg([e.get("return_15m") for e in similar]),
        "avg_return_1h": _safe_avg([e.get("return_1h") for e in similar]),
        "avg_return_4h": _safe_avg([e.get("return_4h") for e in similar]),
        "avg_return_24h": _safe_avg([e.get("return_24h") for e in similar]),
        "avg_max_return": _safe_avg([e.get("max_return") for e in similar]),
        "avg_max_drawdown": _safe_avg([e.get("max_drawdown") for e in similar]),
        "label_distribution": {},
        "avg_by_label": {},
    }

    # 라벨 분포
    for ep in similar:
        label = ep.get("label", "unknown")
        result["label_distribution"][label] = result["label_distribution"].get(label, 0) + 1

    # 라벨별 평균
    for label in result["label_distribution"]:
        label_eps = [e for e in similar if e.get("label") == label]
        result["avg_by_label"][label] = {
            "avg_return_1h": _safe_avg([e.get("return_1h") for e in label_eps]),
            "avg_return_4h": _safe_avg([e.get("return_4h") for e in label_eps]),
            "avg_max_return": _safe_avg([e.get("max_return") for e in label_eps]),
        }

    return result


def _fetch_completed_episodes(conn, symbol):
    """완료된 에피소드 조회 (24h 아웃컴까지 채워진 것)."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT symbol, detected_at, trigger_price, price_change_pct, direction,
                   oi_change_pct, short_liq_count, short_liq_usd,
                   long_liq_count, long_liq_usd,
                   depth_imbalance, bid_depth_1pct, ask_depth_1pct,
                   funding_rate, funding_rate_delta,
                   whale_net_buy_usd, ls_ratio, volume_surge_ratio,
                   return_5m, return_15m, return_1h, return_4h, return_24h,
                   max_return, max_drawdown, label, id
            FROM move_episode
            WHERE symbol = %s AND label IS NOT NULL
            ORDER BY detected_at DESC
            LIMIT 500
        """, (symbol,))

        columns = [
            "symbol", "detected_at", "trigger_price", "price_change_pct", "direction",
            "oi_change_pct", "short_liq_count", "short_liq_usd",
            "long_liq_count", "long_liq_usd",
            "depth_imbalance", "bid_depth_1pct", "ask_depth_1pct",
            "funding_rate", "funding_rate_delta",
            "whale_net_buy_usd", "ls_ratio", "volume_surge_ratio",
            "return_5m", "return_15m", "return_1h", "return_4h", "return_24h",
            "max_return", "max_drawdown", "label", "id",
        ]

        episodes = []
        for row in cur.fetchall():
            ep = {}
            for i, col in enumerate(columns):
                val = row[i]
                # Decimal → float 변환
                if hasattr(val, "is_finite"):
                    val = float(val)
                ep[col] = val
            episodes.append(ep)

        cur.close()
        return episodes

    except Exception as e:
        logger.error(f"완료 에피소드 조회 오류: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _safe_avg(values):
    """None 제외 평균."""
    filtered = [v for v in values if v is not None]
    if not filtered:
        return None
    return round(sum(filtered) / len(filtered), 4)
