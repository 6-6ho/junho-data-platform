"""
Dynamic Theme Discovery DAG
- Runs daily at UTC 21:00 (KST 06:00)
- Fetches previous day's 5m klines from Binance for all USDT-M futures
- Clusters coins by daily high-time proximity using DBSCAN
- Stores clusters + members into dynamic_theme_cluster / dynamic_theme_member
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta, timezone
import logging
import time
import math
import requests
import numpy as np

logger = logging.getLogger(__name__)

default_args = {
    "owner": "junho",
    "depends_on_past": False,
    "start_date": datetime(2026, 1, 9),
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

BINANCE_KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"
BATCH_SLEEP = 0.15  # Rate limit: ~6 req/s


def _fetch_klines(symbol: str, start_ms: int, end_ms: int, interval: str = "5m", limit: int = 288) -> list:
    """Fetch klines from Binance Futures API for a specific time range."""
    try:
        resp = requests.get(
            BINANCE_KLINES_URL,
            params={
                "symbol": symbol,
                "interval": interval,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": limit,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"Failed to fetch klines for {symbol}: {e}")
        return []


def _circular_distance_minutes(t1_min: float, t2_min: float, period: float = 1440.0) -> float:
    """Circular distance in minutes (handles day wrap-around)."""
    diff = abs(t1_min - t2_min)
    return min(diff, period - diff)


def discover_themes(**context):
    """
    Main task: fetch klines, find daily highs, cluster by time proximity.
    """
    from sklearn.cluster import DBSCAN

    pg_hook = PostgresHook(postgres_conn_id="postgres_default")
    conn = pg_hook.get_conn()
    cur = conn.cursor()

    try:
        # Determine target date from Airflow execution_date
        ds = context.get("ds")  # "YYYY-MM-DD"
        if ds:
            target_date = datetime.strptime(ds, "%Y-%m-%d").date()
        else:
            target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

        # Time range for the target date (UTC 00:00 ~ 23:59:59)
        day_start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1) - timedelta(milliseconds=1)
        start_ms = int(day_start.timestamp() * 1000)
        end_ms = int(day_end.timestamp() * 1000)
        logger.info(f"Target date: {target_date} (ds={ds}), range: {day_start} ~ {day_end}")

        # 1. Get symbol list from market_snapshot
        cur.execute("SELECT DISTINCT symbol FROM market_snapshot WHERE symbol LIKE '%USDT'")
        symbols = [row[0] for row in cur.fetchall()]
        logger.info(f"Found {len(symbols)} symbols in market_snapshot")

        if not symbols:
            logger.warning("No symbols found. Skipping.")
            return

        # 2. Fetch klines and extract daily high info
        high_data = []  # (symbol, high_time_minutes, high_price, high_change_pct)

        for i, symbol in enumerate(symbols):
            klines = _fetch_klines(symbol, start_ms, end_ms)
            if not klines or len(klines) < 10:
                continue

            # Find the candle with the highest price
            best_high = 0
            best_idx = 0
            open_price = float(klines[0][1])  # First candle open

            for j, k in enumerate(klines):
                high = float(k[2])  # High price
                if high > best_high:
                    best_high = high
                    best_idx = j

            if open_price <= 0:
                continue

            high_change_pct = ((best_high - open_price) / open_price) * 100

            # Only include coins with meaningful move (>= 3% from open)
            if high_change_pct < 3.0:
                continue

            # High time as minutes from midnight UTC
            high_ts = klines[best_idx][0] / 1000  # ms -> s
            high_dt = datetime.fromtimestamp(high_ts, tz=timezone.utc)
            high_minutes = high_dt.hour * 60 + high_dt.minute

            high_data.append({
                "symbol": symbol,
                "high_time_minutes": high_minutes,
                "high_time_dt": high_dt,
                "high_price": best_high,
                "high_change_pct": high_change_pct,
            })

            if (i + 1) % 50 == 0:
                logger.info(f"Fetched {i + 1}/{len(symbols)} symbols")
            time.sleep(BATCH_SLEEP)

        logger.info(f"Got high data for {len(high_data)} symbols")

        if len(high_data) < 5:
            logger.warning(f"Not enough significant movers ({len(high_data)}). Skipping.")
            return

        # 3. DBSCAN clustering on high time (circular distance)
        minutes_array = np.array([d["high_time_minutes"] for d in high_data]).reshape(-1, 1)

        # Pre-compute circular distance matrix
        n = len(high_data)
        dist_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                d = _circular_distance_minutes(minutes_array[i, 0], minutes_array[j, 0])
                dist_matrix[i, j] = d
                dist_matrix[j, i] = d

        clustering = DBSCAN(eps=15, min_samples=3, metric="precomputed").fit(dist_matrix)
        labels = clustering.labels_

        unique_labels = set(labels)
        unique_labels.discard(-1)  # Remove noise
        logger.info(f"Found {len(unique_labels)} clusters (noise: {list(labels).count(-1)} coins)")

        if not unique_labels:
            logger.info("No clusters found. All coins are noise.")
            return

        # 4. Calculate cluster stats and save
        # Delete existing data for target_date (idempotent re-run)
        cur.execute("DELETE FROM dynamic_theme_cluster WHERE created_date = %s", (target_date,))

        for label in sorted(unique_labels):
            members = [high_data[i] for i in range(n) if labels[i] == label]
            coin_count = len(members)

            times_min = [m["high_time_minutes"] for m in members]
            changes = [m["high_change_pct"] for m in members]

            # Average high time (circular mean)
            angles = [t * 2 * math.pi / 1440 for t in times_min]
            mean_sin = sum(math.sin(a) for a in angles) / len(angles)
            mean_cos = sum(math.cos(a) for a in angles) / len(angles)
            mean_angle = math.atan2(mean_sin, mean_cos)
            if mean_angle < 0:
                mean_angle += 2 * math.pi
            avg_minutes = mean_angle * 1440 / (2 * math.pi)

            # Time spread (circular std dev in minutes)
            R = math.sqrt(mean_sin**2 + mean_cos**2)
            if R >= 1:
                time_spread = 0
            else:
                time_spread = math.sqrt(-2 * math.log(R)) * 1440 / (2 * math.pi)

            avg_change = sum(changes) / len(changes)

            # Strength = (coin_count * avg_high_change_pct) / (time_spread + 1)
            strength = (coin_count * avg_change) / (time_spread + 1)

            # Convert avg_minutes back to timestamptz for target_date
            avg_hour = int(avg_minutes // 60)
            avg_min = int(avg_minutes % 60)
            avg_high_time = datetime(
                target_date.year, target_date.month, target_date.day,
                avg_hour, avg_min, tzinfo=timezone.utc,
            )

            cur.execute(
                """
                INSERT INTO dynamic_theme_cluster
                    (created_date, coin_count, strength_score, avg_high_time,
                     time_spread_minutes, avg_high_change_pct)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING cluster_id
                """,
                (target_date, coin_count, strength, avg_high_time, time_spread, avg_change),
            )
            cluster_id = cur.fetchone()[0]

            # Insert members
            for m in members:
                cur.execute(
                    """
                    INSERT INTO dynamic_theme_member
                        (cluster_id, symbol, high_time, high_price, high_change_pct)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (cluster_id, m["symbol"], m["high_time_dt"], m["high_price"], m["high_change_pct"]),
                )

            logger.info(
                f"Cluster {cluster_id}: {coin_count} coins, "
                f"strength={strength:.2f}, avg_time={avg_hour:02d}:{avg_min:02d}UTC, "
                f"spread={time_spread:.1f}min, avg_change={avg_change:.2f}%"
            )

        conn.commit()
        logger.info("Dynamic theme discovery completed successfully.")

    except Exception as e:
        logger.error(f"Dynamic theme discovery failed: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


with DAG(
    "dynamic_theme_discovery",
    default_args=default_args,
    description="Discover dynamic themes via high-time DBSCAN clustering (daily)",
    schedule_interval="0 21 * * *",
    catchup=False,
    tags=["theme", "analysis", "trade"],
) as dag:

    discover_task = PythonOperator(
        task_id="discover_themes",
        python_callable=discover_themes,
    )
