"""
Whale Monitor API — 에피소드 + 실시간 데이터 조회
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/api/whale", tags=["whale"])


@router.get("/dashboard")
def whale_dashboard(db: Session = Depends(get_db)):
    """현재 실시간 상태: 호가깊이, 최근 고래거래, 청산, OI."""
    # 최신 호가 깊이
    depth = db.execute(text("""
        SELECT mid_price, bid_depth_1pct, ask_depth_1pct,
               bid_depth_5pct, ask_depth_5pct, depth_imbalance, recorded_at
        FROM orderbook_depth
        WHERE symbol = 'BTCUSDT'
        ORDER BY recorded_at DESC LIMIT 1
    """)).fetchone()

    # 최근 5분 청산 집계
    liqs = db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE side = 'BUY') AS short_liq_count,
            COALESCE(SUM(notional_usd) FILTER (WHERE side = 'BUY'), 0) AS short_liq_usd,
            COUNT(*) FILTER (WHERE side = 'SELL') AS long_liq_count,
            COALESCE(SUM(notional_usd) FILTER (WHERE side = 'SELL'), 0) AS long_liq_usd
        FROM liquidation_event
        WHERE symbol = 'BTCUSDT' AND event_time > NOW() - INTERVAL '5 minutes'
    """)).fetchone()

    # 최근 고래 거래 10건
    whales = db.execute(text("""
        SELECT side, price, quantity, notional_usd, trade_time
        FROM whale_trade
        WHERE symbol = 'BTCUSDT'
        ORDER BY trade_time DESC LIMIT 10
    """)).fetchall()

    # 최근 온체인 이체 5건
    transfers = db.execute(text("""
        SELECT chain, amount, amount_usd, from_label, to_label, direction, block_time
        FROM whale_transfer
        ORDER BY recorded_at DESC LIMIT 5
    """)).fetchall()

    return {
        "depth": {
            "mid_price": float(depth[0]) if depth else None,
            "bid_depth_1pct": float(depth[1]) if depth else None,
            "ask_depth_1pct": float(depth[2]) if depth else None,
            "bid_depth_5pct": float(depth[3]) if depth else None,
            "ask_depth_5pct": float(depth[4]) if depth else None,
            "depth_imbalance": float(depth[5]) if depth else None,
            "recorded_at": depth[6].isoformat() if depth else None,
        } if depth else None,
        "liquidations_5m": {
            "short_liq_count": liqs[0] if liqs else 0,
            "short_liq_usd": float(liqs[1]) if liqs else 0,
            "long_liq_count": liqs[2] if liqs else 0,
            "long_liq_usd": float(liqs[3]) if liqs else 0,
        },
        "recent_whale_trades": [
            {
                "side": w[0],
                "price": float(w[1]),
                "quantity": float(w[2]),
                "notional_usd": float(w[3]),
                "trade_time": w[4].isoformat(),
            }
            for w in whales
        ],
        "recent_transfers": [
            {
                "chain": t[0],
                "amount": float(t[1]),
                "amount_usd": float(t[2]) if t[2] else None,
                "from_label": t[3],
                "to_label": t[4],
                "direction": t[5],
                "block_time": t[6].isoformat() if t[6] else None,
            }
            for t in transfers
        ],
    }


@router.get("/episodes")
def whale_episodes(
    limit: int = Query(20, ge=1, le=100),
    label: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """에피소드 목록 (최근, 필터 가능)."""
    conditions = ["TRUE"]
    params = {"limit": limit}

    if label:
        conditions.append("label = :label")
        params["label"] = label
    if direction:
        conditions.append("direction = :direction")
        params["direction"] = direction

    where = " AND ".join(conditions)

    rows = db.execute(text(f"""
        SELECT id, symbol, detected_at, trigger_price, price_change_pct, direction,
               oi_change_pct, short_liq_count, short_liq_usd, long_liq_count, long_liq_usd,
               depth_imbalance, funding_rate, whale_net_buy_usd,
               return_5m, return_15m, return_1h, return_4h, return_24h,
               max_return, max_drawdown, label
        FROM move_episode
        WHERE {where}
        ORDER BY detected_at DESC
        LIMIT :limit
    """), params).fetchall()

    episodes = []
    for r in rows:
        episodes.append({
            "id": r[0],
            "symbol": r[1],
            "detected_at": r[2].isoformat() if r[2] else None,
            "trigger_price": float(r[3]) if r[3] else None,
            "price_change_pct": float(r[4]) if r[4] else None,
            "direction": r[5],
            "oi_change_pct": float(r[6]) if r[6] else None,
            "short_liq_count": r[7],
            "short_liq_usd": float(r[8]) if r[8] else None,
            "long_liq_count": r[9],
            "long_liq_usd": float(r[10]) if r[10] else None,
            "depth_imbalance": float(r[11]) if r[11] else None,
            "funding_rate": float(r[12]) if r[12] else None,
            "whale_net_buy_usd": float(r[13]) if r[13] else None,
            "return_5m": float(r[14]) if r[14] else None,
            "return_15m": float(r[15]) if r[15] else None,
            "return_1h": float(r[16]) if r[16] else None,
            "return_4h": float(r[17]) if r[17] else None,
            "return_24h": float(r[18]) if r[18] else None,
            "max_return": float(r[19]) if r[19] else None,
            "max_drawdown": float(r[20]) if r[20] else None,
            "label": r[21],
        })

    return {"episodes": episodes, "count": len(episodes)}


@router.get("/episodes/active")
def whale_active_episodes(db: Session = Depends(get_db)):
    """현재 추적 중인 에피소드 (아웃컴 미완)."""
    rows = db.execute(text("""
        SELECT id, symbol, detected_at, trigger_price, price_change_pct, direction,
               oi_change_pct, short_liq_count, short_liq_usd, long_liq_count, long_liq_usd,
               depth_imbalance, funding_rate, whale_net_buy_usd,
               return_5m, return_15m, return_1h, return_4h, return_24h,
               max_return, max_drawdown, similar_episodes
        FROM move_episode
        WHERE label IS NULL
        ORDER BY detected_at DESC
        LIMIT 10
    """)).fetchall()

    episodes = []
    for r in rows:
        episodes.append({
            "id": r[0],
            "symbol": r[1],
            "detected_at": r[2].isoformat() if r[2] else None,
            "trigger_price": float(r[3]) if r[3] else None,
            "price_change_pct": float(r[4]) if r[4] else None,
            "direction": r[5],
            "oi_change_pct": float(r[6]) if r[6] else None,
            "short_liq_count": r[7],
            "short_liq_usd": float(r[8]) if r[8] else None,
            "long_liq_count": r[9],
            "long_liq_usd": float(r[10]) if r[10] else None,
            "depth_imbalance": float(r[11]) if r[11] else None,
            "funding_rate": float(r[12]) if r[12] else None,
            "whale_net_buy_usd": float(r[13]) if r[13] else None,
            "return_5m": float(r[14]) if r[14] else None,
            "return_15m": float(r[15]) if r[15] else None,
            "return_1h": float(r[16]) if r[16] else None,
            "return_4h": float(r[17]) if r[17] else None,
            "return_24h": float(r[18]) if r[18] else None,
            "max_return": float(r[19]) if r[19] else None,
            "max_drawdown": float(r[20]) if r[20] else None,
            "similar_episodes": r[21],
        })

    return {"episodes": episodes, "count": len(episodes)}


@router.get("/episodes/{episode_id}")
def whale_episode_detail(episode_id: int, db: Session = Depends(get_db)):
    """에피소드 상세 (프로파일 + 아웃컴 + 유사)."""
    r = db.execute(text("""
        SELECT id, symbol, detected_at, trigger_price, price_change_pct, direction,
               oi_change_pct, short_liq_count, short_liq_usd, long_liq_count, long_liq_usd,
               depth_imbalance, bid_depth_1pct, ask_depth_1pct,
               funding_rate, funding_rate_delta, whale_net_buy_usd, ls_ratio, volume_surge_ratio,
               return_5m, return_15m, return_1h, return_4h, return_24h,
               max_return, max_drawdown, label,
               profile_json, similar_episodes
        FROM move_episode WHERE id = :id
    """), {"id": episode_id}).fetchone()

    if not r:
        return {"error": "not found"}

    return {
        "id": r[0],
        "symbol": r[1],
        "detected_at": r[2].isoformat() if r[2] else None,
        "trigger_price": float(r[3]) if r[3] else None,
        "price_change_pct": float(r[4]) if r[4] else None,
        "direction": r[5],
        "profile": {
            "oi_change_pct": float(r[6]) if r[6] else None,
            "short_liq_count": r[7],
            "short_liq_usd": float(r[8]) if r[8] else None,
            "long_liq_count": r[9],
            "long_liq_usd": float(r[10]) if r[10] else None,
            "depth_imbalance": float(r[11]) if r[11] else None,
            "bid_depth_1pct": float(r[12]) if r[12] else None,
            "ask_depth_1pct": float(r[13]) if r[13] else None,
            "funding_rate": float(r[14]) if r[14] else None,
            "funding_rate_delta": float(r[15]) if r[15] else None,
            "whale_net_buy_usd": float(r[16]) if r[16] else None,
            "ls_ratio": float(r[17]) if r[17] else None,
            "volume_surge_ratio": float(r[18]) if r[18] else None,
        },
        "outcomes": {
            "return_5m": float(r[19]) if r[19] else None,
            "return_15m": float(r[20]) if r[20] else None,
            "return_1h": float(r[21]) if r[21] else None,
            "return_4h": float(r[22]) if r[22] else None,
            "return_24h": float(r[23]) if r[23] else None,
            "max_return": float(r[24]) if r[24] else None,
            "max_drawdown": float(r[25]) if r[25] else None,
        },
        "label": r[26],
        "profile_json": r[27],
        "similar_episodes": r[28],
    }


@router.get("/stats")
def whale_stats(db: Session = Depends(get_db)):
    """축적 통계 (총 에피소드, 라벨 분포 등)."""
    total = db.execute(text(
        "SELECT COUNT(*) FROM move_episode"
    )).scalar()

    completed = db.execute(text(
        "SELECT COUNT(*) FROM move_episode WHERE label IS NOT NULL"
    )).scalar()

    active = db.execute(text(
        "SELECT COUNT(*) FROM move_episode WHERE label IS NULL"
    )).scalar()

    label_dist = db.execute(text("""
        SELECT label, COUNT(*),
               AVG(return_1h), AVG(return_4h), AVG(max_return), AVG(max_drawdown)
        FROM move_episode
        WHERE label IS NOT NULL
        GROUP BY label
        ORDER BY COUNT(*) DESC
    """)).fetchall()

    return {
        "total_episodes": total,
        "completed_episodes": completed,
        "active_episodes": active,
        "label_distribution": [
            {
                "label": r[0],
                "count": r[1],
                "avg_return_1h": round(float(r[2]), 2) if r[2] else None,
                "avg_return_4h": round(float(r[3]), 2) if r[3] else None,
                "avg_max_return": round(float(r[4]), 2) if r[4] else None,
                "avg_max_drawdown": round(float(r[5]), 2) if r[5] else None,
            }
            for r in label_dist
        ],
    }
