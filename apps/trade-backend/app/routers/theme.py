"""
Theme RS (Relative Strength) Router
- GET /api/theme/rs               → theme RS ranking (computed from movers_latest)
- GET /api/theme/dynamic          → latest dynamic theme clusters (strength sorted)
- GET /api/theme/dynamic/{id}     → specific cluster coins + market_snapshot join
- GET /api/theme/{id}/coins       → coins in a specific theme with their changes
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

import random
from typing import Dict, Any
from datetime import datetime

from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/theme", tags=["theme"])


@router.get("/rs")
async def get_theme_rs(mock: bool = False, db: Session = Depends(get_db)):
    """
    Calculate theme RS from latest movers data.
    RS = theme_avg_change / market_avg_change
    """
    if mock:
        return _generate_mock_themes()

    try:
        result = db.execute(text("""
            WITH latest AS (
                SELECT MAX(snapshot_time) AS ts FROM theme_rs_snapshot
            )
            SELECT t.theme_id, t.theme_name, t.exclude_from_rs,
                   s.avg_change_pct, s.market_avg_pct, s.rs_score,
                   s.coin_count, s.top_coin, s.top_coin_pct AS best_pct,
                   s.snapshot_time
            FROM theme_master t
            LEFT JOIN theme_rs_snapshot s
              ON s.theme_id = t.theme_id
             AND s.snapshot_time = (SELECT ts FROM latest)
            WHERE t.exclude_from_rs = FALSE
            ORDER BY s.avg_change_pct DESC NULLS LAST
        """))
        themes = [dict(row) for row in result.mappings()]

        # Format timestamp for JSON if exists
        timestamp = None
        if themes and themes[0].get('snapshot_time'):
             timestamp = themes[0]['snapshot_time'].isoformat()

        # Convert Decimal to float
        for t in themes:
            if 'snapshot_time' in t:
                del t['snapshot_time'] # Remove from item, sent as global timestamp
            for k, v in t.items():
                if hasattr(v, '__float__'):
                    t[k] = float(v)

        return {
            "themes": themes,
            "total_themes": len(themes),
            "timestamp": timestamp
        }

    except Exception as e:
        logger.error(f"Failed to calculate theme RS: {e}")
        return {"themes": [], "total_themes": 0, "error": str(e)}


@router.get("/dynamic")
async def get_dynamic_themes(db: Session = Depends(get_db)):
    """Get latest dynamic theme clusters (correlation-based), sorted by strength."""
    try:
        result = db.execute(text("""
            WITH latest AS (
                SELECT MAX(created_date) AS dt FROM dynamic_theme_cluster
            )
            SELECT cluster_id, created_date, coin_count, strength_score,
                   avg_high_change_pct, lead_symbol, lead_change_pct,
                   avg_correlation, created_at
            FROM dynamic_theme_cluster
            WHERE created_date = (SELECT dt FROM latest)
            ORDER BY strength_score DESC
        """))
        clusters = [dict(row) for row in result.mappings()]

        for c in clusters:
            for k, v in c.items():
                if hasattr(v, '__float__'):
                    c[k] = float(v)
            if c.get('created_at'):
                c['created_at'] = c['created_at'].isoformat()
            if c.get('created_date'):
                c['created_date'] = str(c['created_date'])

        return {
            "clusters": clusters,
            "total_clusters": len(clusters),
            "date": clusters[0]["created_date"] if clusters else None,
        }
    except Exception as e:
        logger.error(f"Failed to get dynamic themes: {e}")
        return {"clusters": [], "total_clusters": 0, "error": str(e)}


@router.get("/dynamic/{cluster_id}")
async def get_dynamic_theme_detail(cluster_id: int, db: Session = Depends(get_db)):
    """Get coins in a specific dynamic theme cluster with correlation data."""
    try:
        # Cluster info
        result = db.execute(text("""
            SELECT cluster_id, created_date, coin_count, strength_score,
                   lead_symbol, lead_change_pct, avg_correlation
            FROM dynamic_theme_cluster WHERE cluster_id = :cluster_id
        """), {"cluster_id": cluster_id})
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Cluster not found")
        cluster = dict(row)

        for k, v in cluster.items():
            if hasattr(v, '__float__'):
                cluster[k] = float(v)
            if k == 'created_date' and v:
                cluster[k] = str(v) if not isinstance(v, str) else v

        # Members with correlation data
        result = db.execute(text("""
            SELECT m.symbol, m.daily_change_pct, m.correlation_to_lead,
                   ms.change_pct_24h, ms.vol_ratio
            FROM dynamic_theme_member m
            LEFT JOIN market_snapshot ms ON ms.symbol = m.symbol
            WHERE m.cluster_id = :cluster_id
            ORDER BY m.correlation_to_lead DESC
        """), {"cluster_id": cluster_id})
        members = [dict(row) for row in result.mappings()]

        for m in members:
            for k, v in m.items():
                if hasattr(v, '__float__'):
                    m[k] = float(v)

        return {
            "cluster": cluster,
            "members": members,
            "member_count": len(members),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dynamic theme detail: {e}")
        return {"cluster": None, "members": [], "error": str(e)}


@router.get("/{theme_id}/coins")
async def get_theme_coins(theme_id: int, mock: bool = False, db: Session = Depends(get_db)):
    """Get all coins in a specific theme with their latest changes."""
    if mock:
        return _generate_mock_coins(theme_id)

    try:
        # Get theme info
        result = db.execute(text(
            "SELECT theme_id, theme_name FROM theme_master WHERE theme_id = :theme_id"
        ), {"theme_id": theme_id})
        theme = result.mappings().first()
        if not theme:
            raise HTTPException(status_code=404, detail="Theme not found")
        theme = dict(theme)

        # Get coins with latest price changes
        result = db.execute(text("""
            SELECT
                c.symbol,
                c.name_kr,
                c.listed_period,
                c.note,
                lp.change_pct_24h,
                lp.change_pct_window,
                lp.vol_ratio,
                lp.event_time
            FROM coin_theme_mapping c
            LEFT JOIN market_snapshot lp ON lp.symbol = c.symbol || 'USDT'
            WHERE c.theme_id = :theme_id
            ORDER BY COALESCE(lp.change_pct_24h, 0) DESC
        """), {"theme_id": theme_id})
        coins = [dict(row) for row in result.mappings()]

        for c in coins:
            for k, v in c.items():
                if hasattr(v, '__float__'):
                    c[k] = float(v)
            if c.get('event_time'):
                c['event_time'] = c['event_time'].isoformat()

        return {
            "theme": theme,
            "coins": coins,
            "coin_count": len(coins)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get theme coins: {e}")
        return {"theme": None, "coins": [], "error": str(e)}


def _generate_mock_themes(count: int = 15) -> Dict[str, Any]:
    """Generate mock theme RS data."""
    themes = []
    market_avg = random.uniform(-2.0, 5.0)

    theme_names = [
        "AI", "Meme", "Layer1", "DeFi", "Gaming", "Storage", "Metaverse",
        "ZK-Rollup", "Solana Ecosystem", "BTC Ecology", "RWA", "Oracle",
        "DEX", "Lending", "Privacy"
    ]

    for i in range(count):
        theme_name = theme_names[i] if i < len(theme_names) else f"Theme {i+1}"
        theme_avg = market_avg + random.uniform(-10.0, 20.0)
        rs_score = theme_avg / market_avg if market_avg != 0 else 1.0

        themes.append({
            "theme_id": i + 1,
            "theme_name": theme_name,
            "exclude_from_rs": False,
            "coin_count": random.randint(3, 20),
            "avg_change_pct": round(theme_avg, 2),
            "market_avg_pct": round(market_avg, 2),
            "rs_score": round(rs_score, 2),
            "top_coin": f"COIN{i}",
            "top_coin_name": f"코인{i}",
            "best_pct": round(theme_avg + random.uniform(5.0, 15.0), 2)
        })

    # Sort by avg_change_pct desc
    themes.sort(key=lambda x: x["avg_change_pct"], reverse=True)

    return {
        "themes": themes,
        "total_themes": len(themes),
        "timestamp": datetime.now().isoformat()
    }


def _generate_mock_coins(theme_id: int, count: int = 8) -> Dict[str, Any]:
    """Generate mock coins for a theme."""
    coins = []

    for i in range(count):
        change = random.uniform(-15.0, 30.0)
        coins.append({
            "symbol": f"MOCK{i+1}",
            "name_kr": f"예시코인{i+1}",
            "listed_period": "2024",
            "note": None,
            "change_pct_24h": round(change, 2),
            "change_pct_window": round(change / 2, 2),
            "vol_ratio": round(random.uniform(0.5, 5.0), 2),
            "event_time": datetime.now().isoformat()
        })

    coins.sort(key=lambda x: x["change_pct_24h"], reverse=True)

    return {
        "theme": {"theme_id": theme_id, "theme_name": f"Mock Theme {theme_id}"},
        "coins": coins,
        "coin_count": len(coins)
    }
