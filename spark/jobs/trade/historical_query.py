"""
Historical Query CLI — 과거 시점 데이터 재현 유틸리티

Usage:
    python historical_query.py --date 2025-02-15
    python historical_query.py --date 2025-02-15 --symbol BTCUSDT
    python historical_query.py --date 2025-02-15 --output report.json
"""
import argparse
import json
import os
import sys
from datetime import datetime

import psycopg2

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "app"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
}

WIN_THRESHOLD_PCT = 1.0


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def fetch_signals(cur, target_date, symbol=None):
    """해당 날짜의 시그널 목록 조회."""
    query = """
        SELECT symbol, alert_type, alert_time, entry_price, timeseries_data, created_at
        FROM trade_performance_timeseries
        WHERE alert_time::date = %s
    """
    params = [target_date]
    if symbol:
        query += " AND symbol = %s"
        params.append(symbol)
    query += " ORDER BY alert_time"
    cur.execute(query, params)
    return cur.fetchall()


def fetch_snapshots(cur, target_date, symbol=None):
    """해당 날짜의 원본 스냅샷 조회."""
    query = """
        SELECT symbol, alert_time, entry_price, klines_1m, created_at
        FROM signal_raw_snapshot
        WHERE alert_time::date = %s
    """
    params = [target_date]
    if symbol:
        query += " AND symbol = %s"
        params.append(symbol)
    query += " ORDER BY alert_time"
    cur.execute(query, params)
    return cur.fetchall()


def fetch_validations(cur, target_date):
    """해당 날짜 시그널에 대한 검증 로그 조회."""
    query = """
        SELECT symbol, alert_time, stored_profit_pct, recalc_profit_pct,
               diff_pct, status, detail, validated_at
        FROM signal_validation_log
        WHERE alert_time::date = %s
        ORDER BY validated_at
    """
    cur.execute(query, (target_date,))
    return cur.fetchall()


def simulate_tpsl(timeseries_data, take_profit, stop_loss):
    """TP/SL 시뮬레이션 재실행."""
    time_points = []
    for time_str, data in timeseries_data.items():
        time_points.append((int(time_str), data["profit_pct"]))
    time_points.sort(key=lambda x: x[0])

    for t, profit in time_points:
        if profit >= take_profit:
            return {"exit_minute": t, "exit_reason": "TP", "pnl_pct": take_profit}
        elif profit <= -stop_loss:
            return {"exit_minute": t, "exit_reason": "SL", "pnl_pct": -stop_loss}

    if time_points:
        last_t, last_profit = time_points[-1]
        return {"exit_minute": last_t, "exit_reason": "timeout", "pnl_pct": last_profit}

    return {"exit_minute": None, "exit_reason": "no_data", "pnl_pct": 0}


def build_report(target_date, symbol=None):
    """종합 리포트 생성."""
    conn = get_connection()
    cur = conn.cursor()

    signals = fetch_signals(cur, target_date, symbol)
    snapshots = fetch_snapshots(cur, target_date, symbol)
    validations = fetch_validations(cur, target_date)

    # 스냅샷 lookup
    snapshot_map = {}
    for row in snapshots:
        key = (row[0], row[1].isoformat())
        snapshot_map[key] = {
            "entry_price": row[2],
            "klines_count": len(row[3]) if row[3] else 0,
            "created_at": row[4].isoformat(),
        }

    # 검증 lookup
    validation_map = {}
    for row in validations:
        key = (row[0], row[1].isoformat())
        if key not in validation_map:
            validation_map[key] = []
        validation_map[key].append({
            "stored_profit_pct": row[2],
            "recalc_profit_pct": row[3],
            "diff_pct": row[4],
            "status": row[5],
            "detail": row[6],
            "validated_at": row[7].isoformat(),
        })

    # TP/SL 조합으로 시뮬레이션
    tp_levels = [3, 5, 7, 10]
    sl_levels = [1, 2, 3]

    signal_reports = []
    for row in signals:
        sym, alert_type, alert_time, entry_price, ts_data, created_at = row
        if isinstance(ts_data, str):
            ts_data = json.loads(ts_data)

        key = (sym, alert_time.isoformat())

        # 시뮬레이션 재실행
        simulations = {}
        for tp in tp_levels:
            for sl in sl_levels:
                if tp > sl:
                    label = f"TP{tp}_SL{sl}"
                    simulations[label] = simulate_tpsl(ts_data, tp, sl)

        signal_reports.append({
            "symbol": sym,
            "alert_type": alert_type,
            "alert_time": alert_time.isoformat(),
            "entry_price": entry_price,
            "timeseries_summary": {
                "data_points": len(ts_data),
                "max_profit": max((v["profit_pct"] for v in ts_data.values()), default=0),
                "min_profit": min((v["profit_pct"] for v in ts_data.values()), default=0),
                "final_profit": ts_data.get("60", {}).get("profit_pct"),
            },
            "snapshot": snapshot_map.get(key),
            "validations": validation_map.get(key, []),
            "simulations": simulations,
            "created_at": created_at.isoformat(),
        })

    report = {
        "query_date": target_date,
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_signals": len(signals),
            "total_snapshots": len(snapshots),
            "total_validations": len(validations),
            "validation_pass": sum(1 for v in validations if v[5] == 'pass'),
            "validation_fail": sum(1 for v in validations if v[5] == 'fail'),
            "validation_error": sum(1 for v in validations if v[5] == 'error'),
        },
        "signals": signal_reports,
    }

    cur.close()
    conn.close()
    return report


def main():
    parser = argparse.ArgumentParser(description="Historical Query — 과거 시점 데이터 재현")
    parser.add_argument("--date", required=True, help="Target date (YYYY-MM-DD)")
    parser.add_argument("--symbol", help="Filter by symbol (e.g., BTCUSDT)")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    args = parser.parse_args()

    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print(f"Invalid date format: {args.date}. Use YYYY-MM-DD.", file=sys.stderr)
        sys.exit(1)

    report = build_report(args.date, args.symbol)

    output = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Report saved to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
