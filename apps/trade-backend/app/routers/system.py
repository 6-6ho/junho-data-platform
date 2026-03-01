"""
System Control Router
- GET /api/system/mode → current mode
- POST /api/system/mode → change mode (trade/shop/off)
- GET /api/system/performance → latest performance analysis results

Mode state is stored in Postgres (system_config table).
Actual service start/stop is triggered via Airflow DAG API.
"""
import logging
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import psycopg2
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/app")
AIRFLOW_API_URL = os.getenv("AIRFLOW_API_URL", "http://airflow-webserver:8080/api/v1")
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")


def get_db_conn():
    return psycopg2.connect(DATABASE_URL)


def ensure_system_config_table():
    """Create system_config table if not exists."""
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            # Insert default mode if not exists
            cur.execute("""
                INSERT INTO system_config (key, value)
                VALUES ('active_mode', 'off')
                ON CONFLICT (key) DO NOTHING
            """)
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to ensure system_config table: {e}")
        conn.rollback()
    finally:
        conn.close()


# Initialize table on module load
try:
    ensure_system_config_table()
except Exception:
    pass


class ModeRequest(BaseModel):
    mode: str  # "trade" | "shop" | "off"


@router.get("/mode")
async def get_current_mode():
    """Get the current active mode."""
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value, updated_at FROM system_config WHERE key = 'active_mode'")
            row = cur.fetchone()
            if row:
                return {
                    "mode": row[0],
                    "updated_at": row[1].isoformat() if row[1] else None,
                }
            return {"mode": "off", "updated_at": None}
    except Exception as e:
        logger.error(f"Failed to get mode: {e}")
        return {"mode": "unknown", "error": str(e)}
    finally:
        conn.close()


@router.post("/mode")
async def set_mode(req: ModeRequest):
    """Change the active service mode."""
    if req.mode not in ("trade", "shop", "off"):
        raise HTTPException(status_code=400, detail="Invalid mode. Use: trade, shop, off")

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            # Get current mode
            cur.execute("SELECT value FROM system_config WHERE key = 'active_mode'")
            row = cur.fetchone()
            old_mode = row[0] if row else "off"

            # Update mode
            cur.execute("""
                INSERT INTO system_config (key, value, updated_at)
                VALUES ('active_mode', %s, NOW())
                ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = NOW()
            """, (req.mode, req.mode))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to set mode: {e}")
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    finally:
        conn.close()

    # Trigger Airflow DAGs based on mode change
    triggered_dags = []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            auth = (AIRFLOW_USER, AIRFLOW_PASSWORD)

            # Stop old mode services
            if old_mode == "trade" and req.mode != "trade":
                await _trigger_dag(client, auth, "service_trade_stop")
                triggered_dags.append("service_trade_stop")
            elif old_mode == "shop" and req.mode != "shop":
                await _trigger_dag(client, auth, "service_shop_stop")
                triggered_dags.append("service_shop_stop")

            # Start new mode services
            if req.mode == "trade":
                await _trigger_dag(client, auth, "service_trade_start")
                triggered_dags.append("service_trade_start")
            elif req.mode == "shop":
                await _trigger_dag(client, auth, "service_shop_start")
                triggered_dags.append("service_shop_start")
    except Exception as e:
        logger.warning(f"Airflow trigger failed (mode still saved): {e}")

    return {
        "status": "ok",
        "mode": req.mode,
        "previous_mode": old_mode,
        "triggered_dags": triggered_dags,
        "timestamp": datetime.now().isoformat(),
    }


async def _trigger_dag(client, auth, dag_id):
    """Trigger an Airflow DAG run."""
    url = f"{AIRFLOW_API_URL}/dags/{dag_id}/dagRuns"
    try:
        resp = await client.post(
            url,
            json={"conf": {}},
            auth=auth,
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code in (200, 201):
            logger.info(f"Triggered DAG: {dag_id}")
        else:
            logger.warning(f"DAG trigger response {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.warning(f"Failed to trigger DAG {dag_id}: {e}")



@router.get("/performance")
async def get_performance_summary():
    """Get latest performance analysis results."""
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            # Get summary for last 7 days
            cur.execute("""
                SELECT
                    analysis_window_minutes,
                    COUNT(*) as total_signals,
                    SUM(CASE WHEN is_win THEN 1 ELSE 0 END) as wins,
                    ROUND(AVG(max_profit_pct)::numeric, 2) as avg_max_profit,
                    ROUND(AVG(max_drawdown_pct)::numeric, 2) as avg_max_drawdown,
                    ROUND(AVG(final_profit_pct)::numeric, 2) as avg_final_profit,
                    MAX(max_profit_pct) as best_profit,
                    MIN(max_drawdown_pct) as worst_drawdown
                FROM trade_performance
                WHERE created_at >= NOW() - INTERVAL '7 days'
                GROUP BY analysis_window_minutes
                ORDER BY analysis_window_minutes
            """)
            rows = cur.fetchall()

            summary = []
            for row in rows:
                window, total, wins, avg_max, avg_dd, avg_final, best, worst = row
                summary.append({
                    "window_minutes": window,
                    "total_signals": total,
                    "wins": wins,
                    "win_rate": round((wins / total) * 100, 1) if total > 0 else 0,
                    "avg_max_profit": float(avg_max) if avg_max else 0,
                    "avg_max_drawdown": float(avg_dd) if avg_dd else 0,
                    "avg_final_profit": float(avg_final) if avg_final else 0,
                    "best_profit": float(best) if best else 0,
                    "worst_drawdown": float(worst) if worst else 0,
                })

            # Get recent individual results (last 20)
            cur.execute("""
                SELECT symbol, alert_type, alert_time,
                       analysis_window_minutes,
                       max_profit_pct, max_drawdown_pct, final_profit_pct,
                       is_win, result_type
                FROM trade_performance
                WHERE analysis_window_minutes = 60
                ORDER BY created_at DESC
                LIMIT 20
            """)
            recent = cur.fetchall()
            recent_results = []
            for r in recent:
                recent_results.append({
                    "symbol": r[0],
                    "alert_type": r[1],
                    "alert_time": r[2].isoformat() if r[2] else None,
                    "window_minutes": r[3],
                    "max_profit_pct": float(r[4]),
                    "max_drawdown_pct": float(r[5]),
                    "final_profit_pct": float(r[6]),
                    "is_win": r[7],
                    "result_type": r[8],
                    "window_minutes": r[3]
                })

            return {
                "summary": summary,
                "recent": recent_results,
            }
    except Exception as e:
        logger.error(f"Failed to get performance: {e}")
        return {"summary": [], "recent": [], "error": str(e)}
    finally:
        conn.close()


@router.get("/schedule")
async def get_schedule_info():
    """Get the current schedule configuration."""
    return {
        "schedule": [
            {"time": "Always", "action": "Trade Mode Active (24/7)", "tz": "KST"},
        ],
        "note": "System is now consolidated to Trade Mode only.",
    }


@router.get("/performance/time-based")
async def get_time_based_performance(days: int = 7):
    """
    Get time-based performance analysis (5min intervals from 5min to 240min).

    Calculates win rate and profit ratio for each 5-minute interval
    across all signals in the specified time period.

    Returns:
        - summary: Total signals analyzed, date range
        - time_intervals: List of 48 time points with win_rate and profit_ratio
        - best_intervals: Time points with highest win rate and profit ratio
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            # Fetch all timeseries data
            cur.execute("""
                SELECT timeseries_data
                FROM trade_performance_timeseries
                WHERE created_at >= NOW() - INTERVAL '%s days'
            """ % days)

            rows = cur.fetchall()

            if not rows:
                return {
                    "summary": {"total_signals": 0},
                    "time_intervals": [],
                    "best_intervals": {}
                }

            # Aggregate stats per time interval
            time_stats = {}  # {5: {wins: 0, losses: 0, total_profit: 0, ...}, 10: {...}, ...}

            for row in rows:
                ts_data = row[0]  # JSONB

                for time_min_str, data in ts_data.items():
                    time_min = int(time_min_str)

                    if time_min not in time_stats:
                        time_stats[time_min] = {
                            "wins": 0,
                            "losses": 0,
                            "total_profit": 0.0,
                            "total_loss": 0.0
                        }

                    stats = time_stats[time_min]
                    profit_pct = data["profit_pct"]
                    is_win = data["is_win"]

                    if is_win:
                        stats["wins"] += 1
                        stats["total_profit"] += profit_pct
                    else:
                        stats["losses"] += 1
                        if profit_pct < 0:
                            stats["total_loss"] += abs(profit_pct)

            # Calculate metrics per interval
            time_intervals = []
            for time_min in sorted(time_stats.keys()):
                stats = time_stats[time_min]
                total = stats["wins"] + stats["losses"]

                avg_profit = stats["total_profit"] / stats["wins"] if stats["wins"] > 0 else 0
                avg_loss = stats["total_loss"] / stats["losses"] if stats["losses"] > 0 else 1
                profit_ratio = avg_profit / avg_loss if avg_loss > 0 else 0

                time_intervals.append({
                    "time_minutes": time_min,
                    "total_signals": total,
                    "wins": stats["wins"],
                    "losses": stats["losses"],
                    "win_rate": round((stats["wins"] / total) * 100, 1) if total > 0 else 0,
                    "avg_profit": round(avg_profit, 2),
                    "avg_loss": round(avg_loss, 2),
                    "profit_ratio": round(profit_ratio, 2)
                })

            # Find best intervals
            if time_intervals:
                best_win_rate = max(time_intervals, key=lambda x: x["win_rate"])
                best_profit_ratio = max(time_intervals, key=lambda x: x["profit_ratio"])

                return {
                    "summary": {
                        "total_signals": len(rows),
                        "date_range_days": days
                    },
                    "time_intervals": time_intervals,
                    "best_intervals": {
                        "highest_win_rate": {
                            "time_minutes": best_win_rate["time_minutes"],
                            "win_rate": best_win_rate["win_rate"]
                        },
                        "highest_profit_ratio": {
                            "time_minutes": best_profit_ratio["time_minutes"],
                            "profit_ratio": best_profit_ratio["profit_ratio"]
                        }
                    }
                }
            else:
                return {
                    "summary": {"total_signals": 0},
                    "time_intervals": [],
                    "best_intervals": {}
                }
    except Exception as e:
        logger.error(f"Failed to get time-based performance: {e}")
        return {"summary": {"total_signals": 0}, "time_intervals": [], "error": str(e)}
    finally:
        conn.close()
