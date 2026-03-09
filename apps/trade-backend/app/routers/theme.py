"""
Theme RS (Relative Strength) Router
- GET /api/theme/rs               → theme RS ranking (computed from movers_latest)
- GET /api/theme/dynamic          → latest dynamic theme clusters (strength sorted)
- GET /api/theme/dynamic/{id}     → specific cluster coins + market_snapshot join
- GET /api/theme/{id}/coins       → coins in a specific theme with their changes
"""
import logging
import os
from fastapi import APIRouter, HTTPException
import psycopg2
import psycopg2.extras

import random
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/theme", tags=["theme"])

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/app")


def get_db_conn():
    return psycopg2.connect(DATABASE_URL)

@router.get("/rs")
async def get_theme_rs(mock: bool = False):
    """
    Calculate theme RS from latest movers data.
    RS = theme_avg_change / market_avg_change
    """
    if mock:
        return _generate_mock_themes()

    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # ... existing query logic ...
            # Query latest snapshot
            cur.execute("""
                SELECT
                    t.theme_id,
                    t.theme_name,
                    t.exclude_from_rs,
                    s.avg_change_pct,
                    s.market_avg_pct,
                    s.rs_score,
                    s.coin_count,
                    s.top_coin,
                    s.top_coin_pct as best_pct,
                    s.snapshot_time
                FROM theme_master t
                LEFT JOIN theme_rs_snapshot s ON t.theme_id = s.theme_id
                WHERE t.exclude_from_rs = FALSE
                  AND (s.snapshot_time = (SELECT MAX(snapshot_time) FROM theme_rs_snapshot) OR s.snapshot_time IS NULL)
                ORDER BY s.avg_change_pct DESC NULLS LAST
            """)
            themes = cur.fetchall()
            
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
    finally:
        conn.close()


@router.get("/dynamic")
async def get_dynamic_themes():
    """Get latest dynamic theme clusters (correlation-based), sorted by strength."""
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT cluster_id, created_date, coin_count, strength_score,
                       avg_high_change_pct, lead_symbol, lead_change_pct,
                       avg_correlation, created_at
                FROM dynamic_theme_cluster
                WHERE created_date = (SELECT MAX(created_date) FROM dynamic_theme_cluster)
                ORDER BY strength_score DESC
            """)
            clusters = cur.fetchall()

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
    finally:
        conn.close()


@router.get("/dynamic/{cluster_id}")
async def get_dynamic_theme_detail(cluster_id: int):
    """Get coins in a specific dynamic theme cluster with correlation data."""
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Cluster info
            cur.execute("""
                SELECT cluster_id, created_date, coin_count, strength_score,
                       lead_symbol, lead_change_pct, avg_correlation
                FROM dynamic_theme_cluster WHERE cluster_id = %s
            """, (cluster_id,))
            cluster = cur.fetchone()
            if not cluster:
                raise HTTPException(status_code=404, detail="Cluster not found")

            for k, v in cluster.items():
                if hasattr(v, '__float__'):
                    cluster[k] = float(v)
                if k == 'created_date' and v:
                    cluster[k] = str(v) if not isinstance(v, str) else v

            # Members with correlation data
            cur.execute("""
                SELECT m.symbol, m.daily_change_pct, m.correlation_to_lead,
                       ms.change_pct_24h, ms.vol_ratio
                FROM dynamic_theme_member m
                LEFT JOIN market_snapshot ms ON ms.symbol = m.symbol
                WHERE m.cluster_id = %s
                ORDER BY m.correlation_to_lead DESC
            """, (cluster_id,))
            members = cur.fetchall()

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
    finally:
        conn.close()


@router.get("/{theme_id}/coins")
async def get_theme_coins(theme_id: int, mock: bool = False):
    """Get all coins in a specific theme with their latest changes."""
    if mock:
        return _generate_mock_coins(theme_id)

    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Get theme info
            cur.execute("SELECT theme_id, theme_name FROM theme_master WHERE theme_id = %s", (theme_id,))
            theme = cur.fetchone()
            if not theme:
                raise HTTPException(status_code=404, detail="Theme not found")

            # Get coins with latest price changes
            cur.execute("""
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
                WHERE c.theme_id = %s
                ORDER BY COALESCE(lp.change_pct_24h, 0) DESC
            """, (theme_id,))
            coins = cur.fetchall()

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
    finally:
        conn.close()


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
