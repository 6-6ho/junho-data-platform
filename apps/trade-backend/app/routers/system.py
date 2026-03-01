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


def get_date_filter_sql(days: int) -> str:
    """Generate SQL date filter. days=0 means no filter (all data)."""
    if days <= 0:
        return "TRUE"  # No filter
    return f"created_at >= NOW() - INTERVAL '{days} days'"


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



@router.get("/schedule")
async def get_schedule_info():
    """Get the current schedule configuration."""
    return {
        "schedule": [
            {"time": "Always", "action": "Trade Mode Active (24/7)", "tz": "KST"},
        ],
        "note": "System is now consolidated to Trade Mode only.",
    }


@router.get("/performance/profit-targets")
async def get_profit_target_analysis(days: int = 15):
    """
    Analyze hit rate for different profit targets.

    For each target (1%, 2%, 3%...), calculates:
    - hit_rate: % of signals that reached the target within 60min
    - avg_time_to_hit: average minutes to reach target (for signals that hit)

    days=0 returns all data.
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            date_filter = get_date_filter_sql(days)
            cur.execute(f"""
                SELECT timeseries_data
                FROM trade_performance_timeseries
                WHERE {date_filter}
            """)

            rows = cur.fetchall()

            if not rows:
                return {"summary": {"total_signals": 0}, "targets": []}

            # Analyze each target: 0.5%, 1%, 1.5%, 2%, ... 10%
            targets = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
            target_stats = {t: {"hits": 0, "total_time": 0} for t in targets}
            total_signals = len(rows)

            for row in rows:
                ts_data = row[0]

                # For each target, check if it was hit and when
                for target in targets:
                    hit_time = None
                    for time_min in range(1, 61):
                        time_key = str(time_min)
                        if time_key in ts_data:
                            profit_pct = ts_data[time_key]["profit_pct"]
                            if profit_pct >= target:
                                hit_time = time_min
                                break

                    if hit_time:
                        target_stats[target]["hits"] += 1
                        target_stats[target]["total_time"] += hit_time

            # Calculate results
            results = []
            for target in targets:
                stats = target_stats[target]
                hits = stats["hits"]
                hit_rate = round((hits / total_signals) * 100, 1) if total_signals > 0 else 0
                avg_time = round(stats["total_time"] / hits, 1) if hits > 0 else None

                results.append({
                    "target_pct": target,
                    "hits": hits,
                    "hit_rate": hit_rate,
                    "avg_time_to_hit": avg_time
                })

            return {
                "summary": {
                    "total_signals": total_signals,
                    "date_range_days": days
                },
                "targets": results
            }
    except Exception as e:
        logger.error(f"Failed to get profit target analysis: {e}")
        return {"summary": {"total_signals": 0}, "targets": [], "error": str(e)}
    finally:
        conn.close()


@router.get("/performance/time-based")
async def get_time_based_performance(days: int = 15):
    """
    Get time-based performance analysis (5min intervals from 5min to 240min).

    Calculates win rate and profit ratio for each 5-minute interval
    across all signals in the specified time period.

    days=0 returns all data.

    Returns:
        - summary: Total signals analyzed, date range
        - time_intervals: List of 48 time points with win_rate and profit_ratio
        - best_intervals: Time points with highest win rate and profit ratio
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            # Fetch all timeseries data
            date_filter = get_date_filter_sql(days)
            cur.execute(f"""
                SELECT timeseries_data
                FROM trade_performance_timeseries
                WHERE {date_filter}
            """)

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


@router.get("/performance/drawdown-recovery")
async def get_drawdown_recovery_analysis(days: int = 15, target_profit: float = 1.0):
    """
    Analyze recovery probability after different drawdown levels.

    For each signal:
    1. Find the max drawdown (lowest point) within 60 minutes
    2. Check if price recovered to target_profit% after that low point
    3. Group by drawdown level and calculate recovery rate

    This helps determine optimal stop-loss levels. days=0 returns all data.

    Returns:
        - summary: Total signals, date range
        - drawdown_levels: Recovery rate for each drawdown level
        - recommendation: Suggested stop-loss level
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            date_filter = get_date_filter_sql(days)
            cur.execute(f"""
                SELECT timeseries_data
                FROM trade_performance_timeseries
                WHERE {date_filter}
            """)

            rows = cur.fetchall()

            if not rows:
                return {
                    "summary": {"total_signals": 0},
                    "drawdown_levels": [],
                    "recommendation": None
                }

            # Drawdown buckets: -0.5%, -1%, -1.5%, -2%, -2.5%, -3%, -4%, -5%, -7%, -10%
            drawdown_buckets = [-0.5, -1.0, -1.5, -2.0, -2.5, -3.0, -4.0, -5.0, -7.0, -10.0]
            # Cumulative stats: for each level, count signals that went AT LEAST this deep
            bucket_stats = {b: {"total": 0, "recovered": 0} for b in drawdown_buckets}

            for row in rows:
                ts_data = row[0]

                # Convert to sorted list by time
                time_points = []
                for time_str, data in ts_data.items():
                    time_points.append((int(time_str), data["profit_pct"]))
                time_points.sort(key=lambda x: x[0])

                if not time_points:
                    continue

                # Find max drawdown point and its time
                min_profit = float('inf')
                min_time = 0
                for t, profit in time_points:
                    if profit < min_profit:
                        min_profit = profit
                        min_time = t

                # Check recovery after the lowest point
                recovered = False
                for t, profit in time_points:
                    if t > min_time and profit >= target_profit:
                        recovered = True
                        break

                # Assign to ALL buckets where drawdown reached that level (cumulative)
                for bucket in drawdown_buckets:
                    if min_profit <= bucket:
                        bucket_stats[bucket]["total"] += 1
                        if recovered:
                            bucket_stats[bucket]["recovered"] += 1

            # Calculate results
            results = []
            recommended_stoploss = None

            for bucket in drawdown_buckets:
                stats = bucket_stats[bucket]
                if stats["total"] > 0:
                    recovery_rate = round((stats["recovered"] / stats["total"]) * 100, 1)
                    results.append({
                        "drawdown_pct": bucket,
                        "signals": stats["total"],
                        "recovered": stats["recovered"],
                        "recovery_rate": recovery_rate
                    })

                    # Recommend stop-loss where recovery rate drops below 30%
                    if recovery_rate < 30 and recommended_stoploss is None:
                        recommended_stoploss = bucket

            return {
                "summary": {
                    "total_signals": len(rows),
                    "date_range_days": days,
                    "target_profit_pct": target_profit
                },
                "drawdown_levels": results,
                "recommendation": {
                    "stop_loss_pct": recommended_stoploss,
                    "explanation": f"{abs(recommended_stoploss)}% 이상 하락 시 {target_profit}% 회복 확률 30% 미만" if recommended_stoploss else "데이터 부족"
                } if recommended_stoploss else None
            }
    except Exception as e:
        logger.error(f"Failed to get drawdown recovery analysis: {e}")
        return {"summary": {"total_signals": 0}, "drawdown_levels": [], "error": str(e)}
    finally:
        conn.close()


@router.get("/performance/simulate")
async def simulate_trading_strategy(
    take_profit: float = 2.0,
    stop_loss: float = 2.5,
    days: int = 15
):
    """
    Simulate a trading strategy with given take-profit and stop-loss levels.

    For each signal:
    1. Iterate through 1-60 minutes
    2. If price reaches +take_profit% first → book profit
    3. If price reaches -stop_loss% first → book loss
    4. If neither within 60min → use final price

    days=0 returns all data.
    Returns daily P&L, total stats, and strategy performance metrics.
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            date_filter = get_date_filter_sql(days)
            cur.execute(f"""
                SELECT symbol, alert_time, timeseries_data
                FROM trade_performance_timeseries
                WHERE {date_filter}
                ORDER BY alert_time
            """)

            rows = cur.fetchall()

            if not rows:
                return {"summary": {"total_signals": 0}, "trades": [], "daily_pnl": []}

            trades = []
            daily_pnl = {}

            for symbol, alert_time, ts_data in rows:
                # Sort by time
                time_points = []
                for time_str, data in ts_data.items():
                    time_points.append((int(time_str), data["profit_pct"]))
                time_points.sort(key=lambda x: x[0])

                if not time_points:
                    continue

                # Simulate trade
                result_pct = None
                result_type = None
                exit_time = None

                for t, profit in time_points:
                    if profit >= take_profit:
                        result_pct = take_profit
                        result_type = "TP"  # Take Profit
                        exit_time = t
                        break
                    elif profit <= -stop_loss:
                        result_pct = -stop_loss
                        result_type = "SL"  # Stop Loss
                        exit_time = t
                        break

                # If neither TP nor SL hit, use last available price
                if result_pct is None:
                    last_point = time_points[-1]
                    result_pct = last_point[1]
                    result_type = "TIMEOUT"
                    exit_time = last_point[0]

                trade = {
                    "symbol": symbol,
                    "alert_time": alert_time.isoformat() if alert_time else None,
                    "result_pct": round(result_pct, 2),
                    "result_type": result_type,
                    "exit_time_min": exit_time
                }
                trades.append(trade)

                # Aggregate daily P&L
                if alert_time:
                    day_key = alert_time.strftime("%Y-%m-%d")
                    if day_key not in daily_pnl:
                        daily_pnl[day_key] = {"trades": 0, "pnl": 0.0, "wins": 0, "losses": 0}
                    daily_pnl[day_key]["trades"] += 1
                    daily_pnl[day_key]["pnl"] += result_pct
                    if result_pct > 0:
                        daily_pnl[day_key]["wins"] += 1
                    else:
                        daily_pnl[day_key]["losses"] += 1

            # Calculate summary stats
            total_trades = len(trades)
            wins = sum(1 for t in trades if t["result_pct"] > 0)
            losses = sum(1 for t in trades if t["result_pct"] < 0)
            breakeven = total_trades - wins - losses

            total_pnl = sum(t["result_pct"] for t in trades)
            avg_pnl = total_pnl / total_trades if total_trades > 0 else 0

            tp_count = sum(1 for t in trades if t["result_type"] == "TP")
            sl_count = sum(1 for t in trades if t["result_type"] == "SL")
            timeout_count = sum(1 for t in trades if t["result_type"] == "TIMEOUT")

            avg_win = sum(t["result_pct"] for t in trades if t["result_pct"] > 0) / wins if wins > 0 else 0
            avg_loss = sum(t["result_pct"] for t in trades if t["result_pct"] < 0) / losses if losses > 0 else 0

            # Daily P&L list
            daily_list = []
            for day, stats in sorted(daily_pnl.items()):
                daily_list.append({
                    "date": day,
                    "trades": stats["trades"],
                    "pnl": round(stats["pnl"], 2),
                    "wins": stats["wins"],
                    "losses": stats["losses"],
                    "win_rate": round((stats["wins"] / stats["trades"]) * 100, 1) if stats["trades"] > 0 else 0
                })

            return {
                "strategy": {
                    "take_profit_pct": take_profit,
                    "stop_loss_pct": stop_loss
                },
                "summary": {
                    "total_trades": total_trades,
                    "wins": wins,
                    "losses": losses,
                    "breakeven": breakeven,
                    "win_rate": round((wins / total_trades) * 100, 1) if total_trades > 0 else 0,
                    "total_pnl": round(total_pnl, 2),
                    "avg_pnl_per_trade": round(avg_pnl, 3),
                    "avg_win": round(avg_win, 2),
                    "avg_loss": round(avg_loss, 2),
                    "profit_factor": round(abs(avg_win * wins) / abs(avg_loss * losses), 2) if losses > 0 and avg_loss != 0 else 0,
                    "tp_hits": tp_count,
                    "sl_hits": sl_count,
                    "timeouts": timeout_count
                },
                "daily_pnl": daily_list,
                "recent_trades": trades[-20:]  # Last 20 trades
            }
    except Exception as e:
        logger.error(f"Failed to simulate strategy: {e}")
        return {"summary": {"total_trades": 0}, "error": str(e)}
    finally:
        conn.close()


@router.get("/performance/optimize")
async def find_optimal_strategy(days: int = 15):
    """
    Test multiple take-profit and stop-loss combinations to find optimal strategy.

    Tests combinations:
    - Take profit: 3~10%
    - Stop loss: 1~5% (only TP > SL combinations)

    days=0 returns all data.
    Returns top strategies ranked by total P&L and profit factor.
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            date_filter = get_date_filter_sql(days)
            cur.execute(f"""
                SELECT symbol, alert_time, timeseries_data
                FROM trade_performance_timeseries
                WHERE {date_filter}
            """)

            rows = cur.fetchall()

            if not rows:
                return {"summary": {"total_signals": 0}, "strategies": []}

            # Preprocess all signals
            signals = []
            for symbol, alert_time, ts_data in rows:
                time_points = []
                for time_str, data in ts_data.items():
                    time_points.append((int(time_str), data["profit_pct"]))
                time_points.sort(key=lambda x: x[0])
                if time_points:
                    signals.append(time_points)

            # Test combinations (TP: 3~10%, SL: 1~5%, only TP > SL)
            tp_levels = [3, 4, 5, 6, 7, 8, 9, 10]
            sl_levels = [1, 2, 3, 4, 5]

            results = []

            for tp in tp_levels:
                for sl in sl_levels:
                    if tp <= sl:  # Skip invalid combinations
                        continue
                    total_pnl = 0
                    wins = 0
                    losses = 0
                    total_win_pnl = 0
                    total_loss_pnl = 0

                    for time_points in signals:
                        result_pct = None

                        for t, profit in time_points:
                            if profit >= tp:
                                result_pct = tp
                                break
                            elif profit <= -sl:
                                result_pct = -sl
                                break

                        if result_pct is None:
                            result_pct = time_points[-1][1]

                        total_pnl += result_pct
                        if result_pct > 0:
                            wins += 1
                            total_win_pnl += result_pct
                        elif result_pct < 0:
                            losses += 1
                            total_loss_pnl += abs(result_pct)

                    total_trades = len(signals)
                    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
                    profit_factor = (total_win_pnl / total_loss_pnl) if total_loss_pnl > 0 else 0
                    avg_pnl = total_pnl / total_trades if total_trades > 0 else 0

                    results.append({
                        "take_profit": tp,
                        "stop_loss": sl,
                        "total_pnl": round(total_pnl, 2),
                        "avg_pnl": round(avg_pnl, 3),
                        "win_rate": round(win_rate, 1),
                        "wins": wins,
                        "losses": losses,
                        "profit_factor": round(profit_factor, 2)
                    })

            # Sort by avg P&L (better metric than total which scales with signal count)
            results_by_pnl = sorted(results, key=lambda x: x["avg_pnl"], reverse=True)
            # Sort by profit factor (for risk-adjusted)
            results_by_pf = sorted(results, key=lambda x: x["profit_factor"], reverse=True)

            return {
                "summary": {
                    "total_signals": len(signals),
                    "date_range_days": days,
                    "combinations_tested": len(results)
                },
                "best_by_pnl": results_by_pnl[:5],
                "best_by_profit_factor": results_by_pf[:5],
                "all_results": results,  # Full list for heatmap
                "recommendation": results_by_pnl[0] if results_by_pnl else None
            }
    except Exception as e:
        logger.error(f"Failed to optimize strategy: {e}")
        return {"summary": {"total_signals": 0}, "error": str(e)}
    finally:
        conn.close()


@router.get("/performance/weekly-pnl")
async def weekly_pnl(
    take_profit: float = 5.0,
    stop_loss: float = 2.0,
    days: int = 0
):
    """
    Weekly avg PnL and win rate for a given TP/SL strategy.
    Used to visualize strategy performance trend over time.
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            date_filter = get_date_filter_sql(days)
            cur.execute(f"""
                SELECT symbol, alert_time, timeseries_data
                FROM trade_performance_timeseries
                WHERE {date_filter}
                ORDER BY alert_time
            """)
            rows = cur.fetchall()

            if not rows:
                return {"weeks": []}

            # Group signals by ISO week
            from collections import defaultdict
            weekly = defaultdict(list)

            for symbol, alert_time, ts_data in rows:
                time_points = []
                for time_str, data in ts_data.items():
                    time_points.append((int(time_str), data["profit_pct"]))
                time_points.sort(key=lambda x: x[0])
                if not time_points:
                    continue

                # Simulate TP/SL result
                result_pct = None
                for t, profit in time_points:
                    if profit >= take_profit:
                        result_pct = take_profit
                        break
                    elif profit <= -stop_loss:
                        result_pct = -stop_loss
                        break
                if result_pct is None:
                    result_pct = time_points[-1][1]

                week_key = alert_time.isocalendar()[:2]  # (year, week)
                weekly[week_key].append(result_pct)

            # Build weekly summary
            weeks = []
            for (year, week_num), pnls in sorted(weekly.items()):
                wins = sum(1 for p in pnls if p > 0)
                total = len(pnls)
                weeks.append({
                    "week": f"{year}-W{week_num:02d}",
                    "trades": total,
                    "wins": wins,
                    "win_rate": round((wins / total) * 100, 1) if total > 0 else 0,
                    "avg_pnl": round(sum(pnls) / total, 3) if total > 0 else 0,
                })

            return {"weeks": weeks}
    except Exception as e:
        logger.error(f"Failed to get weekly PnL: {e}")
        return {"weeks": [], "error": str(e)}
    finally:
        conn.close()


@router.get("/performance/compound")
async def simulate_compound_growth(
    take_profit: float = 5.0,
    stop_loss: float = 1.0,
    position_size_pct: float = 10.0,
    initial_seed: float = 1000.0,
    days: int = 15
):
    """
    Simulate compound growth with position sizing.

    Parameters:
    - take_profit: Take profit % (default 5%)
    - stop_loss: Stop loss % (default 1%)
    - position_size_pct: % of seed to use per trade (default 10%)
    - initial_seed: Starting capital (default 1000)
    - days: Days to simulate (0 = all data)

    Returns daily seed growth with compound interest.
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            date_filter = get_date_filter_sql(days)
            cur.execute(f"""
                SELECT symbol, alert_time, timeseries_data
                FROM trade_performance_timeseries
                WHERE {date_filter}
                ORDER BY alert_time
            """)

            rows = cur.fetchall()

            if not rows:
                return {"error": "No data"}

            # Process trades in chronological order
            seed = initial_seed
            position_ratio = position_size_pct / 100.0

            daily_seed = {}
            trade_results = []

            for symbol, alert_time, ts_data in rows:
                time_points = []
                for time_str, data in ts_data.items():
                    time_points.append((int(time_str), data["profit_pct"]))
                time_points.sort(key=lambda x: x[0])

                if not time_points:
                    continue

                # Determine trade result
                result_pct = None
                for t, profit in time_points:
                    if profit >= take_profit:
                        result_pct = take_profit
                        break
                    elif profit <= -stop_loss:
                        result_pct = -stop_loss
                        break

                if result_pct is None:
                    result_pct = time_points[-1][1]

                # Calculate P&L with position sizing
                position_value = seed * position_ratio
                pnl = position_value * (result_pct / 100.0)
                seed += pnl

                trade_results.append({
                    "symbol": symbol,
                    "result_pct": result_pct,
                    "pnl": round(pnl, 2),
                    "seed_after": round(seed, 2)
                })

                # Track daily seed
                if alert_time:
                    day_key = alert_time.strftime("%Y-%m-%d")
                    daily_seed[day_key] = round(seed, 2)

            # Calculate metrics
            total_return_pct = ((seed - initial_seed) / initial_seed) * 100
            daily_list = [{"date": k, "seed": v} for k, v in sorted(daily_seed.items())]

            # Calculate daily returns
            daily_returns = []
            prev_seed = initial_seed
            for item in daily_list:
                daily_return = ((item["seed"] - prev_seed) / prev_seed) * 100
                daily_returns.append({
                    "date": item["date"],
                    "seed": item["seed"],
                    "daily_return_pct": round(daily_return, 2)
                })
                prev_seed = item["seed"]

            # Project future growth (assuming same daily avg return)
            avg_daily_return = total_return_pct / days if days > 0 else 0

            projections = {
                "1_week": round(initial_seed * ((1 + avg_daily_return/100) ** 7), 0),
                "1_month": round(initial_seed * ((1 + avg_daily_return/100) ** 30), 0),
                "3_months": round(initial_seed * ((1 + avg_daily_return/100) ** 90), 0),
                "6_months": round(initial_seed * ((1 + avg_daily_return/100) ** 180), 0),
                "1_year": round(initial_seed * ((1 + avg_daily_return/100) ** 365), 0),
            }

            return {
                "strategy": {
                    "take_profit_pct": take_profit,
                    "stop_loss_pct": stop_loss,
                    "position_size_pct": position_size_pct
                },
                "result": {
                    "initial_seed": initial_seed,
                    "final_seed": round(seed, 2),
                    "total_return_pct": round(total_return_pct, 2),
                    "total_trades": len(trade_results),
                    "avg_daily_return_pct": round(avg_daily_return, 2)
                },
                "daily_growth": daily_returns,
                "projections": projections,
                "recent_trades": trade_results[-10:]
            }
    except Exception as e:
        logger.error(f"Failed to simulate compound growth: {e}")
        return {"error": str(e)}
    finally:
        conn.close()
