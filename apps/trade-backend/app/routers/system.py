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
from collections import defaultdict
from datetime import datetime, date
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
import httpx

from app.database import engine, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])

AIRFLOW_API_URL = os.getenv("AIRFLOW_API_URL", "http://airflow-webserver:8080/api/v1")
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")

# Pre-computed TP/SL grid: (2.0, 2.5) + tp=[3..10] x sl=[1..5] where tp>sl
_PRECOMPUTED_TPSL = {(2.0, 2.5)}
for _tp in range(3, 11):
    for _sl in range(1, 6):
        if _tp > _sl:
            _PRECOMPUTED_TPSL.add((float(_tp), float(_sl)))

# Profit target columns in mart_trade_signal_detail
_TARGET_COLS = [
    (0.5, "hit_min_0_5"), (1.0, "hit_min_1_0"), (1.5, "hit_min_1_5"),
    (2.0, "hit_min_2_0"), (2.5, "hit_min_2_5"), (3.0, "hit_min_3_0"),
    (3.5, "hit_min_3_5"), (4.0, "hit_min_4_0"), (4.5, "hit_min_4_5"),
    (5.0, "hit_min_5_0"), (6.0, "hit_min_6_0"), (7.0, "hit_min_7_0"),
    (8.0, "hit_min_8_0"), (9.0, "hit_min_9_0"), (10.0, "hit_min_10_0"),
]


# ---------------------------------------------------------------------------
# Filter helpers
# ---------------------------------------------------------------------------

def get_date_filter_sql(days: int, prefix: str = "") -> str:
    """Generate SQL date filter. days=0 means no filter (all data)."""
    if days <= 0:
        return "TRUE"
    return f"{prefix}alert_time >= NOW() - INTERVAL '{days} days'"


def _mart_tier_filter(tier: str, col: str = "tier") -> str:
    """For tables with tier = 'High'/'Mid'/'Small'. 'all' means no filter."""
    if not tier or tier.lower() == "all":
        return "TRUE"
    tier_map = {"high": "High", "mid": "Mid", "small": "Small"}
    t = tier_map.get(tier.lower())
    return f"{col} = '{t}'" if t else "TRUE"


def _mart_time_tier_filter(tier: str) -> str:
    """For mart_trade_time_performance where 'all' is a stored tier value."""
    if not tier or tier.lower() == "all":
        return "tier = 'all'"
    tier_map = {"high": "High", "mid": "Mid", "small": "Small"}
    t = tier_map.get(tier.lower())
    return f"tier = '{t}'" if t else "tier = 'all'"


def _mart_date_filter(days: int) -> str:
    """Date filter for mart tables using 'date' column."""
    if days <= 0:
        return "TRUE"
    return f"date >= CURRENT_DATE - {days}"


# ---------------------------------------------------------------------------
# Legacy helpers — kept for JSONB fallback on non-precomputed TP/SL
# ---------------------------------------------------------------------------

def _build_timeseries_query(select_cols: str, days: int, tier: str = None, order_by: str = None) -> str:
    date_filter = get_date_filter_sql(days, "t.")
    cte = ""
    join = ""
    tier_where = ""

    if tier and tier != "all":
        cte = """WITH tier_movers AS (
            SELECT DISTINCT ON (symbol, event_time) symbol, event_time, status
            FROM movers_latest WHERE type = 'rise'
            ORDER BY symbol, event_time, change_pct_window DESC
        )"""
        join = "JOIN tier_movers m ON m.symbol = t.symbol AND m.event_time = t.alert_time"
        tier_map = {"high": "[High]%", "mid": "[Mid]%", "small": "[Small]%"}
        pattern = tier_map.get(tier.lower())
        if pattern:
            tier_where = f"AND m.status LIKE '{pattern}'"

    order = f"ORDER BY {order_by}" if order_by else ""
    return f"""
        {cte}
        SELECT {select_cols}
        FROM trade_performance_timeseries t
        {join}
        WHERE {date_filter} {tier_where}
        {order}
    """


def _fetch_timeseries_rows(db, days, tier=None):
    sql = _build_timeseries_query("t.symbol, t.alert_time, t.timeseries_data", days, tier, "t.alert_time")
    return db.execute(text(sql)).fetchall()


def _preprocess_timeseries(rows):
    return [
        (symbol, alert_time,
         sorted([(int(k), v["profit_pct"]) for k, v in ts_data.items()], key=lambda x: x[0]))
        for symbol, alert_time, ts_data in rows
        if ts_data
    ]


def _simulate_tpsl_results(preprocessed, take_profit: float, stop_loss: float):
    results = []
    for symbol, alert_time, time_points in preprocessed:
        if not time_points:
            continue
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
        results.append((symbol, alert_time, result_pct))
    return results


# ---------------------------------------------------------------------------
# System config / mode endpoints (unchanged)
# ---------------------------------------------------------------------------

def ensure_system_config_table():
    """Create system_config table if not exists."""
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            conn.execute(text("""
                INSERT INTO system_config (key, value)
                VALUES ('active_mode', 'off')
                ON CONFLICT (key) DO NOTHING
            """))
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to ensure system_config table: {e}")


try:
    ensure_system_config_table()
except Exception:
    pass


class ModeRequest(BaseModel):
    mode: str  # "trade" | "shop" | "off"


@router.get("/mode")
async def get_current_mode(db: Session = Depends(get_db)):
    """Get the current active mode."""
    try:
        row = db.execute(
            text("SELECT value, updated_at FROM system_config WHERE key = 'active_mode'")
        ).fetchone()
        if row:
            return {
                "mode": row[0],
                "updated_at": row[1].isoformat() if row[1] else None,
            }
        return {"mode": "off", "updated_at": None}
    except Exception as e:
        logger.error(f"Failed to get mode: {e}")
        return {"mode": "unknown", "error": str(e)}


@router.post("/mode")
async def set_mode(req: ModeRequest, db: Session = Depends(get_db)):
    """Change the active service mode."""
    if req.mode not in ("trade", "shop", "off"):
        raise HTTPException(status_code=400, detail="Invalid mode. Use: trade, shop, off")

    try:
        row = db.execute(
            text("SELECT value FROM system_config WHERE key = 'active_mode'")
        ).fetchone()
        old_mode = row[0] if row else "off"

        db.execute(text("""
            INSERT INTO system_config (key, value, updated_at)
            VALUES ('active_mode', :mode, NOW())
            ON CONFLICT (key) DO UPDATE SET value = :mode, updated_at = NOW()
        """), {"mode": req.mode})
        db.commit()
    except Exception as e:
        logger.error(f"Failed to set mode: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

    triggered_dags = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            auth = (AIRFLOW_USER, AIRFLOW_PASSWORD)
            if old_mode == "trade" and req.mode != "trade":
                await _trigger_dag(client, auth, "service_trade_stop")
                triggered_dags.append("service_trade_stop")
            elif old_mode == "shop" and req.mode != "shop":
                await _trigger_dag(client, auth, "service_shop_stop")
                triggered_dags.append("service_shop_stop")
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


# ---------------------------------------------------------------------------
# Performance endpoints — mart-based
# ---------------------------------------------------------------------------

@router.get("/performance/profit-targets")
async def get_profit_target_analysis(days: int = 15, tier: str = "all", db: Session = Depends(get_db)):
    """Analyze hit rate for different profit targets. days=0 returns all data."""
    try:
        date_filter = get_date_filter_sql(days)
        tier_filter = _mart_tier_filter(tier)

        cols = ", ".join(f"COUNT({col}), AVG({col})" for _, col in _TARGET_COLS)
        sql = f"""
            SELECT COUNT(*) AS total, {cols}
            FROM mart_trade_signal_detail
            WHERE {date_filter} AND {tier_filter}
        """
        row = db.execute(text(sql)).fetchone()

        if not row or row[0] == 0:
            return {"summary": {"total_signals": 0}, "targets": []}

        total_signals = row[0]
        results = []
        for i, (target, _) in enumerate(_TARGET_COLS):
            hits = row[1 + i * 2] or 0
            avg_time_raw = row[2 + i * 2]
            hit_rate = round((hits / total_signals) * 100, 1) if total_signals > 0 else 0
            avg_time = round(float(avg_time_raw), 1) if avg_time_raw is not None else None
            results.append({
                "target_pct": target,
                "hits": hits,
                "hit_rate": hit_rate,
                "avg_time_to_hit": avg_time,
            })

        return {
            "summary": {"total_signals": total_signals, "date_range_days": days},
            "targets": results,
        }
    except Exception as e:
        logger.error(f"Failed to get profit target analysis: {e}")
        return {"summary": {"total_signals": 0}, "targets": [], "error": str(e)}


@router.get("/performance/time-based")
async def get_time_based_performance(days: int = 15, tier: str = "all", db: Session = Depends(get_db)):
    """Time-based win rate and profit ratio per minute interval. days=0 returns all data."""
    try:
        date_filter = _mart_date_filter(days)
        tier_filter = _mart_time_tier_filter(tier)

        sql = f"""
            SELECT time_min,
                   SUM(total_signals)::int, SUM(wins)::int, SUM(losses)::int,
                   SUM(total_profit), SUM(total_loss)
            FROM mart_trade_time_performance
            WHERE {date_filter} AND {tier_filter}
            GROUP BY time_min ORDER BY time_min
        """
        rows = db.execute(text(sql)).fetchall()

        if not rows:
            return {"summary": {"total_signals": 0}, "time_intervals": [], "best_intervals": {}}

        # total_signals = max across time points (all signals appear at each minute)
        total_signals = max(r[1] for r in rows) if rows else 0

        time_intervals = []
        for r in rows:
            time_min, total, wins, losses, total_profit, total_loss = r
            avg_profit = total_profit / wins if wins > 0 else 0
            avg_loss = total_loss / losses if losses > 0 else 1
            profit_ratio = avg_profit / avg_loss if avg_loss > 0 else 0

            time_intervals.append({
                "time_minutes": time_min,
                "total_signals": total,
                "wins": wins,
                "losses": losses,
                "win_rate": round((wins / total) * 100, 1) if total > 0 else 0,
                "avg_profit": round(avg_profit, 2),
                "avg_loss": round(avg_loss, 2),
                "profit_ratio": round(profit_ratio, 2),
            })

        best_win_rate = max(time_intervals, key=lambda x: x["win_rate"])
        best_profit_ratio = max(time_intervals, key=lambda x: x["profit_ratio"])

        return {
            "summary": {"total_signals": total_signals, "date_range_days": days},
            "time_intervals": time_intervals,
            "best_intervals": {
                "highest_win_rate": {
                    "time_minutes": best_win_rate["time_minutes"],
                    "win_rate": best_win_rate["win_rate"],
                },
                "highest_profit_ratio": {
                    "time_minutes": best_profit_ratio["time_minutes"],
                    "profit_ratio": best_profit_ratio["profit_ratio"],
                },
            },
        }
    except Exception as e:
        logger.error(f"Failed to get time-based performance: {e}")
        return {"summary": {"total_signals": 0}, "time_intervals": [], "error": str(e)}


@router.get("/performance/drawdown-recovery")
async def get_drawdown_recovery_analysis(
    days: int = 15, target_profit: float = 1.0, tier: str = "all",
    db: Session = Depends(get_db),
):
    """Recovery probability after different drawdown levels. days=0 returns all data."""
    try:
        date_filter = get_date_filter_sql(days)
        tier_filter = _mart_tier_filter(tier)

        rows = db.execute(text(f"""
            SELECT max_drawdown, max_profit_after_drawdown
            FROM mart_trade_signal_detail
            WHERE {date_filter} AND {tier_filter}
        """)).fetchall()

        if not rows:
            return {"summary": {"total_signals": 0}, "drawdown_levels": [], "recommendation": None}

        drawdown_buckets = [-0.5, -1.0, -1.5, -2.0, -2.5, -3.0, -4.0, -5.0, -7.0, -10.0]
        bucket_stats = {b: {"total": 0, "recovered": 0} for b in drawdown_buckets}

        for max_dd, max_profit_after_dd in rows:
            recovered = (
                max_profit_after_dd is not None and max_profit_after_dd >= target_profit
            )
            for bucket in drawdown_buckets:
                if max_dd <= bucket:
                    bucket_stats[bucket]["total"] += 1
                    if recovered:
                        bucket_stats[bucket]["recovered"] += 1

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
                    "recovery_rate": recovery_rate,
                })
                if recovery_rate < 30 and recommended_stoploss is None:
                    recommended_stoploss = bucket

        return {
            "summary": {
                "total_signals": len(rows),
                "date_range_days": days,
                "target_profit_pct": target_profit,
            },
            "drawdown_levels": results,
            "recommendation": {
                "stop_loss_pct": recommended_stoploss,
                "explanation": (
                    f"{abs(recommended_stoploss)}% 이상 하락 시 {target_profit}% 회복 확률 30% 미만"
                    if recommended_stoploss else "데이터 부족"
                ),
            } if recommended_stoploss else None,
        }
    except Exception as e:
        logger.error(f"Failed to get drawdown recovery analysis: {e}")
        return {"summary": {"total_signals": 0}, "drawdown_levels": [], "error": str(e)}


@router.get("/performance/simulate")
async def simulate_trading_strategy(
    take_profit: float = 2.0,
    stop_loss: float = 2.5,
    days: int = 15,
    tier: str = "all",
    db: Session = Depends(get_db),
):
    """Simulate TP/SL strategy. Uses mart for precomputed combos, JSONB fallback otherwise."""
    try:
        if (take_profit, stop_loss) in _PRECOMPUTED_TPSL:
            return _simulate_from_mart(take_profit, stop_loss, days, tier, db)
        return _simulate_legacy(take_profit, stop_loss, days, tier, db)
    except Exception as e:
        logger.error(f"Failed to simulate strategy: {e}")
        return {"summary": {"total_trades": 0}, "error": str(e)}


def _simulate_from_mart(take_profit, stop_loss, days, tier, db):
    date_filter = get_date_filter_sql(days)
    tier_filter = _mart_tier_filter(tier)

    rows = db.execute(text(f"""
        SELECT symbol, alert_time, result_pct, result_type, exit_time_min
        FROM mart_trade_strategy_result
        WHERE take_profit = :tp AND stop_loss = :sl
          AND {date_filter} AND {tier_filter}
        ORDER BY alert_time
    """), {"tp": take_profit, "sl": stop_loss}).fetchall()

    if not rows:
        return {"summary": {"total_signals": 0}, "trades": [], "daily_pnl": []}

    trades = []
    daily_pnl = {}
    for symbol, alert_time, result_pct, result_type, exit_time_min in rows:
        trade = {
            "symbol": symbol,
            "alert_time": alert_time.isoformat() if alert_time else None,
            "result_pct": round(result_pct, 2),
            "result_type": result_type,
            "exit_time_min": exit_time_min,
        }
        trades.append(trade)
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

    return _build_simulate_response(trades, daily_pnl, take_profit, stop_loss)


def _simulate_legacy(take_profit, stop_loss, days, tier, db):
    """Fallback for non-precomputed TP/SL combinations."""
    rows = _fetch_timeseries_rows(db, days, tier)
    if not rows:
        return {"summary": {"total_signals": 0}, "trades": [], "daily_pnl": []}

    preprocessed = _preprocess_timeseries(rows)
    trades = []
    daily_pnl = {}

    for symbol, alert_time, time_points in preprocessed:
        if not time_points:
            continue
        result_pct = None
        result_type = None
        exit_time = None
        for t, profit in time_points:
            if profit >= take_profit:
                result_pct = take_profit
                result_type = "TP"
                exit_time = t
                break
            elif profit <= -stop_loss:
                result_pct = -stop_loss
                result_type = "SL"
                exit_time = t
                break
        if result_pct is None:
            result_pct = time_points[-1][1]
            result_type = "TIMEOUT"
            exit_time = time_points[-1][0]

        trade = {
            "symbol": symbol,
            "alert_time": alert_time.isoformat() if alert_time else None,
            "result_pct": round(result_pct, 2),
            "result_type": result_type,
            "exit_time_min": exit_time,
        }
        trades.append(trade)
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

    return _build_simulate_response(trades, daily_pnl, take_profit, stop_loss)


def _build_simulate_response(trades, daily_pnl, take_profit, stop_loss):
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

    daily_list = []
    for day, stats in sorted(daily_pnl.items()):
        daily_list.append({
            "date": day,
            "trades": stats["trades"],
            "pnl": round(stats["pnl"], 2),
            "wins": stats["wins"],
            "losses": stats["losses"],
            "win_rate": round((stats["wins"] / stats["trades"]) * 100, 1) if stats["trades"] > 0 else 0,
        })

    return {
        "strategy": {"take_profit_pct": take_profit, "stop_loss_pct": stop_loss},
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
            "timeouts": timeout_count,
        },
        "daily_pnl": daily_list,
        "recent_trades": trades[-20:],
    }


@router.get("/performance/optimize")
async def find_optimal_strategy(days: int = 15, tier: str = "all", db: Session = Depends(get_db)):
    """Test TP=[3..10] x SL=[1..5] combinations from daily pre-aggregated mart. days=0 returns all data."""
    try:
        date_filter = _mart_date_filter(days)
        tier_filter = _mart_time_tier_filter(tier)

        rows = db.execute(text(f"""
            SELECT take_profit, stop_loss,
                   SUM(trades)::int AS total_trades,
                   SUM(wins)::int AS wins,
                   SUM(losses)::int AS losses,
                   SUM(total_win_pnl) AS total_win_pnl,
                   SUM(total_loss_pnl) AS total_loss_pnl,
                   SUM(total_pnl) AS total_pnl
            FROM mart_trade_optimize_daily
            WHERE take_profit IN (3,4,5,6,7,8,9,10)
              AND stop_loss IN (1,2,3,4,5)
              AND take_profit > stop_loss
              AND {date_filter} AND {tier_filter}
            GROUP BY take_profit, stop_loss
        """)).fetchall()

        if not rows:
            return {"summary": {"total_signals": 0}, "strategies": []}

        # Get total signal count (all combos have same signal count)
        total_signals = rows[0][2] if rows else 0

        results = []
        for tp, sl, total, wins, losses, win_pnl, loss_pnl, total_pnl in rows:
            win_rate = (wins / total) * 100 if total > 0 else 0
            profit_factor = (win_pnl / loss_pnl) if loss_pnl > 0 else 0
            avg_pnl = total_pnl / total if total > 0 else 0
            results.append({
                "take_profit": int(tp),
                "stop_loss": int(sl),
                "total_pnl": round(float(total_pnl), 2),
                "avg_pnl": round(float(avg_pnl), 3),
                "win_rate": round(win_rate, 1),
                "wins": wins,
                "losses": losses,
                "profit_factor": round(float(profit_factor), 2),
            })

        results_by_pnl = sorted(results, key=lambda x: x["avg_pnl"], reverse=True)
        results_by_pf = sorted(results, key=lambda x: x["profit_factor"], reverse=True)

        return {
            "summary": {
                "total_signals": total_signals,
                "date_range_days": days,
                "combinations_tested": len(results),
            },
            "best_by_pnl": results_by_pnl[:5],
            "best_by_profit_factor": results_by_pf[:5],
            "all_results": results,
            "recommendation": results_by_pnl[0] if results_by_pnl else None,
        }
    except Exception as e:
        logger.error(f"Failed to optimize strategy: {e}")
        return {"summary": {"total_signals": 0}, "error": str(e)}


@router.get("/performance/weekly-pnl")
async def weekly_pnl(
    take_profit: float = 5.0,
    stop_loss: float = 2.0,
    days: int = 0,
    tier: str = "all",
    db: Session = Depends(get_db),
):
    """Weekly avg PnL and win rate for a given TP/SL strategy."""
    try:
        if (take_profit, stop_loss) not in _PRECOMPUTED_TPSL:
            return _weekly_pnl_legacy(take_profit, stop_loss, days, tier, db)

        date_filter = get_date_filter_sql(days)
        tier_filter = _mart_tier_filter(tier)

        rows = db.execute(text(f"""
            SELECT EXTRACT(ISOYEAR FROM alert_time)::int AS year,
                   EXTRACT(WEEK FROM alert_time)::int AS week_num,
                   COUNT(*)::int AS trades,
                   SUM(CASE WHEN result_pct > 0 THEN 1 ELSE 0 END)::int AS wins,
                   AVG(result_pct) AS avg_pnl
            FROM mart_trade_strategy_result
            WHERE take_profit = :tp AND stop_loss = :sl
              AND {date_filter} AND {tier_filter}
            GROUP BY 1, 2 ORDER BY 1, 2
        """), {"tp": take_profit, "sl": stop_loss}).fetchall()

        if not rows:
            return {"weeks": []}

        weeks = []
        for year, week_num, trades, wins, avg_pnl in rows:
            mon = date.fromisocalendar(year, week_num, 1)
            weeks.append({
                "week": f"{year}-W{week_num:02d}",
                "label": f"{mon.month}/{mon.day}~",
                "trades": trades,
                "wins": wins,
                "win_rate": round((wins / trades) * 100, 1) if trades > 0 else 0,
                "avg_pnl": round(float(avg_pnl), 3) if avg_pnl else 0,
            })

        return {"weeks": weeks}
    except Exception as e:
        logger.error(f"Failed to get weekly PnL: {e}")
        return {"weeks": [], "error": str(e)}


def _weekly_pnl_legacy(take_profit, stop_loss, days, tier, db):
    rows = _fetch_timeseries_rows(db, days, tier)
    if not rows:
        return {"weeks": []}
    preprocessed = _preprocess_timeseries(rows)
    weekly = defaultdict(list)
    for _, alert_time, result_pct in _simulate_tpsl_results(preprocessed, take_profit, stop_loss):
        week_key = alert_time.isocalendar()[:2]
        weekly[week_key].append(result_pct)
    weeks = []
    for (year, week_num), pnls in sorted(weekly.items()):
        wins = sum(1 for p in pnls if p > 0)
        total = len(pnls)
        mon = date.fromisocalendar(year, week_num, 1)
        weeks.append({
            "week": f"{year}-W{week_num:02d}",
            "label": f"{mon.month}/{mon.day}~",
            "trades": total,
            "wins": wins,
            "win_rate": round((wins / total) * 100, 1) if total > 0 else 0,
            "avg_pnl": round(sum(pnls) / total, 3) if total > 0 else 0,
        })
    return {"weeks": weeks}


@router.get("/performance/daily-pnl")
async def daily_pnl(
    take_profit: float = 5.0,
    stop_loss: float = 2.0,
    days: int = 7,
    tier: str = "all",
    db: Session = Depends(get_db),
):
    """Daily avg PnL and win rate for a given TP/SL strategy."""
    try:
        if (take_profit, stop_loss) not in _PRECOMPUTED_TPSL:
            return _daily_pnl_legacy(take_profit, stop_loss, days, tier, db)

        date_filter = get_date_filter_sql(days)
        tier_filter = _mart_tier_filter(tier)

        rows = db.execute(text(f"""
            SELECT alert_time::date AS day,
                   COUNT(*)::int AS trades,
                   SUM(CASE WHEN result_pct > 0 THEN 1 ELSE 0 END)::int AS wins,
                   AVG(result_pct) AS avg_pnl
            FROM mart_trade_strategy_result
            WHERE take_profit = :tp AND stop_loss = :sl
              AND {date_filter} AND {tier_filter}
            GROUP BY 1 ORDER BY 1
        """), {"tp": take_profit, "sl": stop_loss}).fetchall()

        if not rows:
            return {"days": []}

        result = []
        for day, trades, wins, avg_pnl in rows:
            result.append({
                "date": day.isoformat(),
                "label": f"{day.month}/{day.day}",
                "trades": trades,
                "wins": wins,
                "win_rate": round((wins / trades) * 100, 1) if trades > 0 else 0,
                "avg_pnl": round(float(avg_pnl), 3) if avg_pnl else 0,
            })

        return {"days": result}
    except Exception as e:
        logger.error(f"Failed to get daily PnL: {e}")
        return {"days": [], "error": str(e)}


def _daily_pnl_legacy(take_profit, stop_loss, days, tier, db):
    rows = _fetch_timeseries_rows(db, days, tier)
    if not rows:
        return {"days": []}
    preprocessed = _preprocess_timeseries(rows)
    daily = defaultdict(list)
    for _, alert_time, result_pct in _simulate_tpsl_results(preprocessed, take_profit, stop_loss):
        day_key = alert_time.date()
        daily[day_key].append(result_pct)
    result = []
    for day, pnls in sorted(daily.items()):
        wins = sum(1 for p in pnls if p > 0)
        total = len(pnls)
        result.append({
            "date": day.isoformat(),
            "label": f"{day.month}/{day.day}",
            "trades": total,
            "wins": wins,
            "win_rate": round((wins / total) * 100, 1) if total > 0 else 0,
            "avg_pnl": round(sum(pnls) / total, 3) if total > 0 else 0,
        })
    return {"days": result}


@router.get("/performance/compound")
async def simulate_compound_growth(
    take_profit: float = 5.0,
    stop_loss: float = 1.0,
    position_size_pct: float = 10.0,
    initial_seed: float = 1000.0,
    days: int = 15,
    tier: str = "all",
    db: Session = Depends(get_db),
):
    """Simulate compound growth with position sizing. days=0 returns all data."""
    try:
        if (take_profit, stop_loss) in _PRECOMPUTED_TPSL:
            trade_data = _compound_from_mart(take_profit, stop_loss, days, tier, db)
        else:
            trade_data = _compound_legacy(take_profit, stop_loss, days, tier, db)

        if trade_data is None:
            return {"error": "No data"}

        seed = initial_seed
        position_ratio = position_size_pct / 100.0
        daily_seed = {}
        trade_results = []

        for symbol, alert_time, result_pct in trade_data:
            position_value = seed * position_ratio
            pnl = position_value * (result_pct / 100.0)
            seed += pnl
            trade_results.append({
                "symbol": symbol,
                "result_pct": result_pct,
                "pnl": round(pnl, 2),
                "seed_after": round(seed, 2),
            })
            if alert_time:
                day_key = alert_time.strftime("%Y-%m-%d") if hasattr(alert_time, 'strftime') else str(alert_time)
                daily_seed[day_key] = round(seed, 2)

        total_return_pct = ((seed - initial_seed) / initial_seed) * 100
        daily_list = [{"date": k, "seed": v} for k, v in sorted(daily_seed.items())]

        daily_returns = []
        prev_seed = initial_seed
        for item in daily_list:
            daily_return = ((item["seed"] - prev_seed) / prev_seed) * 100
            daily_returns.append({
                "date": item["date"],
                "seed": item["seed"],
                "daily_return_pct": round(daily_return, 2),
            })
            prev_seed = item["seed"]

        avg_daily_return = total_return_pct / days if days > 0 else 0
        projections = {
            "1_week": round(initial_seed * ((1 + avg_daily_return / 100) ** 7), 0),
            "1_month": round(initial_seed * ((1 + avg_daily_return / 100) ** 30), 0),
            "3_months": round(initial_seed * ((1 + avg_daily_return / 100) ** 90), 0),
            "6_months": round(initial_seed * ((1 + avg_daily_return / 100) ** 180), 0),
            "1_year": round(initial_seed * ((1 + avg_daily_return / 100) ** 365), 0),
        }

        return {
            "strategy": {
                "take_profit_pct": take_profit,
                "stop_loss_pct": stop_loss,
                "position_size_pct": position_size_pct,
            },
            "result": {
                "initial_seed": initial_seed,
                "final_seed": round(seed, 2),
                "total_return_pct": round(total_return_pct, 2),
                "total_trades": len(trade_results),
                "avg_daily_return_pct": round(avg_daily_return, 2),
            },
            "daily_growth": daily_returns,
            "projections": projections,
            "recent_trades": trade_results[-10:],
        }
    except Exception as e:
        logger.error(f"Failed to simulate compound growth: {e}")
        return {"error": str(e)}


def _compound_from_mart(take_profit, stop_loss, days, tier, db):
    """Return list of (symbol, alert_time, result_pct) from mart."""
    date_filter = get_date_filter_sql(days)
    tier_filter = _mart_tier_filter(tier)
    rows = db.execute(text(f"""
        SELECT symbol, alert_time, result_pct
        FROM mart_trade_strategy_result
        WHERE take_profit = :tp AND stop_loss = :sl
          AND {date_filter} AND {tier_filter}
        ORDER BY alert_time
    """), {"tp": take_profit, "sl": stop_loss}).fetchall()
    if not rows:
        return None
    return [(r[0], r[1], r[2]) for r in rows]


def _compound_legacy(take_profit, stop_loss, days, tier, db):
    """Return list of (symbol, alert_time, result_pct) from JSONB."""
    rows = _fetch_timeseries_rows(db, days, tier)
    if not rows:
        return None
    preprocessed = _preprocess_timeseries(rows)
    results = []
    for symbol, alert_time, time_points in preprocessed:
        if not time_points:
            continue
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
        results.append((symbol, alert_time, result_pct))
    return results if results else None


@router.get("/performance/tier-summary")
async def get_tier_summary(days: int = 7, db: Session = Depends(get_db)):
    """Get signal count per tier from mart table."""
    try:
        date_filter = get_date_filter_sql(days)
        row = db.execute(text(f"""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE tier = 'High') AS high,
                COUNT(*) FILTER (WHERE tier = 'Mid') AS mid,
                COUNT(*) FILTER (WHERE tier = 'Small') AS small
            FROM mart_trade_signal_detail
            WHERE {date_filter}
        """)).fetchone()
        if row:
            return {"total": row[0], "high": row[1], "mid": row[2], "small": row[3]}
        return {"total": 0, "high": 0, "mid": 0, "small": 0}
    except Exception as e:
        logger.error(f"Failed to get tier summary: {e}")
        return {"total": 0, "high": 0, "mid": 0, "small": 0, "error": str(e)}
