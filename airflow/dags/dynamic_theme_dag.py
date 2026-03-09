"""
Dynamic Theme Discovery DAG (v3: market-neutral correlation)
- Runs daily at UTC 21:00 (KST 06:00)
- Step 1: Fetch previous day's 5m klines, subtract BTC returns (market neutralization),
          compute pairwise Pearson correlation on neutral returns
- Step 2: Build clusters from 14-day average correlation via Agglomerative Clustering
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta, timezone
import logging
import time
import requests
import numpy as np

logger = logging.getLogger(__name__)

default_args = {
    "owner": "junho",
    "depends_on_past": False,
    "start_date": datetime(2026, 1, 1),
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

BINANCE_KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"
BATCH_SLEEP = 0.15  # Rate limit: ~6 req/s
MIN_CHANGE_PCT = 3.0  # Minimum intraday range to include in correlation
CORR_THRESHOLD = 0.5  # Minimum correlation to store
LOOKBACK_DAYS = 14  # Days of correlation history (crypto narrative cycle)
AGGLO_DIST_THRESHOLD = 0.35  # distance = 1 - corr → corr >= 0.65 to cluster
MIN_CLUSTER_SIZE = 3
MAX_CLUSTER_SIZE = 7


def _fetch_klines(symbol: str, start_ms: int, end_ms: int, interval: str = "5m", limit: int = 288) -> list:
    """Fetch klines from Binance Futures API."""
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


def compute_daily_correlation(**context):
    """
    Step 1: Fetch previous day's 5m klines for all symbols,
    compute pairwise Pearson correlation on 5m returns,
    and store pairs with corr >= 0.5 in daily_correlation.
    Also stores each symbol's daily change % in XCom for Step 2.
    """
    pg_hook = PostgresHook(postgres_conn_id="postgres_default")
    conn = pg_hook.get_conn()
    cur = conn.cursor()

    try:
        # Determine target date
        ds = context.get("ds")
        if ds:
            target_date = datetime.strptime(ds, "%Y-%m-%d").date()
        else:
            target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

        day_start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1) - timedelta(milliseconds=1)
        start_ms = int(day_start.timestamp() * 1000)
        end_ms = int(day_end.timestamp() * 1000)
        logger.info(f"Target date: {target_date}, range: {day_start} ~ {day_end}")

        # Get symbol list
        cur.execute("SELECT DISTINCT symbol FROM market_snapshot WHERE symbol LIKE '%USDT'")
        symbols = [row[0] for row in cur.fetchall()]
        logger.info(f"Found {len(symbols)} symbols")

        if not symbols:
            logger.warning("No symbols found. Skipping.")
            return

        # Fetch BTCUSDT klines for market neutralization
        btc_klines = _fetch_klines('BTCUSDT', start_ms, end_ms)
        btc_returns = None
        if btc_klines and len(btc_klines) >= 50:
            btc_closes = np.array([float(k[4]) for k in btc_klines])
            if btc_closes[0] > 0:
                btc_returns = np.diff(np.log(btc_closes))
                logger.info(f"BTC returns: {len(btc_returns)} periods for market neutralization")
        else:
            logger.warning("Could not fetch BTC klines; skipping market neutralization")
        time.sleep(BATCH_SLEEP)

        # Fetch klines and compute 5m returns
        returns_map = {}  # symbol -> np.array of returns
        change_map = {}   # symbol -> daily change %

        for i, symbol in enumerate(symbols):
            klines = _fetch_klines(symbol, start_ms, end_ms)
            if not klines or len(klines) < 50:
                continue

            closes = np.array([float(k[4]) for k in klines])  # Close prices
            if closes[0] <= 0:
                continue

            # Daily change %
            daily_change = ((closes[-1] - closes[0]) / closes[0]) * 100
            change_map[symbol] = round(daily_change, 4)

            # Intraday range check
            high = np.max(closes)
            low = np.min(closes)
            intraday_range = ((high - low) / low) * 100
            if intraday_range < MIN_CHANGE_PCT:
                continue

            # 5m log returns, market-neutralized (subtract BTC returns)
            rets = np.diff(np.log(closes))
            if btc_returns is not None and len(rets) > 0:
                min_len = min(len(rets), len(btc_returns))
                rets = rets[:min_len] - btc_returns[:min_len]
            if len(rets) > 0 and np.std(rets) > 1e-10:
                returns_map[symbol] = rets

            if (i + 1) % 100 == 0:
                logger.info(f"Fetched {i + 1}/{len(symbols)} symbols, {len(returns_map)} active")
            time.sleep(BATCH_SLEEP)

        logger.info(f"Active symbols (>= {MIN_CHANGE_PCT}% range): {len(returns_map)}, total with change: {len(change_map)}")

        if len(returns_map) < 5:
            logger.warning(f"Not enough active symbols ({len(returns_map)}). Skipping correlation.")
            context["ti"].xcom_push(key="change_map", value=change_map)
            context["ti"].xcom_push(key="target_date", value=str(target_date))
            return

        # Align return arrays to same length
        active_symbols = sorted(returns_map.keys())
        min_len = min(len(returns_map[s]) for s in active_symbols)
        matrix = np.array([returns_map[s][:min_len] for s in active_symbols])

        # Pearson correlation matrix
        corr_matrix = np.corrcoef(matrix)
        n = len(active_symbols)

        # Delete existing data for this date (idempotent)
        cur.execute("DELETE FROM daily_correlation WHERE date = %s", (target_date,))

        # Insert pairs with corr >= threshold
        pairs_count = 0
        batch = []
        for i in range(n):
            for j in range(i + 1, n):
                corr_val = corr_matrix[i, j]
                if np.isnan(corr_val):
                    continue
                if corr_val >= CORR_THRESHOLD:
                    # Store both directions for easier querying
                    sa, sb = active_symbols[i], active_symbols[j]
                    if sa > sb:
                        sa, sb = sb, sa
                    batch.append((target_date, sa, sb, round(float(corr_val), 6)))
                    pairs_count += 1

                    if len(batch) >= 500:
                        cur.executemany(
                            "INSERT INTO daily_correlation (date, symbol_a, symbol_b, correlation) "
                            "VALUES (%s, %s, %s, %s) ON CONFLICT (date, symbol_a, symbol_b) DO UPDATE SET correlation = EXCLUDED.correlation",
                            batch,
                        )
                        batch = []

        if batch:
            cur.executemany(
                "INSERT INTO daily_correlation (date, symbol_a, symbol_b, correlation) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (date, symbol_a, symbol_b) DO UPDATE SET correlation = EXCLUDED.correlation",
                batch,
            )

        conn.commit()
        logger.info(f"Stored {pairs_count} correlation pairs for {target_date}")

        # Push data to XCom for Step 2
        context["ti"].xcom_push(key="change_map", value=change_map)
        context["ti"].xcom_push(key="target_date", value=str(target_date))

    except Exception as e:
        logger.error(f"compute_daily_correlation failed: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def build_clusters(**context):
    """
    Step 2: Build clusters from 14-day average market-neutral correlation.
    - Distance matrix = 1 - avg_corr
    - AgglomerativeClustering(distance_threshold=0.35) → corr >= 0.65 clusters
    - Cluster size filter: 3-7 members only
    - Lead coin = highest avg pairwise correlation in cluster
    """
    from sklearn.cluster import AgglomerativeClustering

    pg_hook = PostgresHook(postgres_conn_id="postgres_default")
    conn = pg_hook.get_conn()
    cur = conn.cursor()

    try:
        # Get data from Step 1
        ti = context["ti"]
        change_map = ti.xcom_pull(task_ids="compute_daily_correlation", key="change_map") or {}
        target_date_str = ti.xcom_pull(task_ids="compute_daily_correlation", key="target_date")

        if not target_date_str:
            ds = context.get("ds")
            target_date = datetime.strptime(ds, "%Y-%m-%d").date() if ds else (datetime.now(timezone.utc) - timedelta(days=1)).date()
        else:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()

        logger.info(f"Building clusters for {target_date}, change_map has {len(change_map)} symbols")

        # Query average correlation over lookback period
        lookback_start = target_date - timedelta(days=LOOKBACK_DAYS - 1)
        cur.execute(
            """
            SELECT symbol_a, symbol_b, AVG(correlation) as avg_corr, COUNT(*) as days
            FROM daily_correlation
            WHERE date BETWEEN %s AND %s
            GROUP BY symbol_a, symbol_b
            HAVING COUNT(*) >= 3
            """,
            (lookback_start, target_date),
        )
        rows = cur.fetchall()
        logger.info(f"Got {len(rows)} symbol pairs with avg correlation (lookback {lookback_start} ~ {target_date})")

        if not rows:
            logger.info("No correlation data available yet. Skipping clustering.")
            return

        # Build symbol set and avg correlation lookup
        symbol_set = set()
        corr_lookup = {}
        for sa, sb, avg_corr, days in rows:
            symbol_set.add(sa)
            symbol_set.add(sb)
            corr_lookup[(sa, sb)] = float(avg_corr)
            corr_lookup[(sb, sa)] = float(avg_corr)

        symbols = sorted(symbol_set)
        n = len(symbols)
        sym_idx = {s: i for i, s in enumerate(symbols)}
        logger.info(f"Building {n}x{n} distance matrix")

        if n < MIN_CLUSTER_SIZE:
            logger.info(f"Not enough symbols ({n}) for clustering.")
            return

        # Build distance matrix (1 - avg_corr)
        dist_matrix = np.ones((n, n))
        np.fill_diagonal(dist_matrix, 0.0)

        for (sa, sb), corr_val in corr_lookup.items():
            i, j = sym_idx.get(sa), sym_idx.get(sb)
            if i is not None and j is not None and i != j:
                dist_matrix[i, j] = 1.0 - corr_val

        # Agglomerative Clustering (hierarchical, average linkage)
        clustering = AgglomerativeClustering(
            metric='precomputed',
            linkage='average',
            distance_threshold=AGGLO_DIST_THRESHOLD,
            n_clusters=None,
        ).fit(dist_matrix)
        labels = clustering.labels_

        unique_labels = set(labels)
        label_counts = {l: list(labels).count(l) for l in unique_labels}
        valid_labels = {l for l, cnt in label_counts.items()
                        if MIN_CLUSTER_SIZE <= cnt <= MAX_CLUSTER_SIZE}
        logger.info(
            f"Agglomerative: {len(unique_labels)} raw clusters, "
            f"{len(valid_labels)} valid (size {MIN_CLUSTER_SIZE}-{MAX_CLUSTER_SIZE})"
        )

        if not valid_labels:
            logger.info("No clusters found.")
            # Still clean up old clusters for this date
            cur.execute("DELETE FROM dynamic_theme_cluster WHERE created_date = %s", (target_date,))
            conn.commit()
            return

        # Delete existing clusters for this date (idempotent)
        cur.execute("DELETE FROM dynamic_theme_cluster WHERE created_date = %s", (target_date,))

        for label in sorted(valid_labels):
            member_indices = [i for i in range(n) if labels[i] == label]
            member_symbols = [symbols[i] for i in member_indices]
            coin_count = len(member_symbols)

            # Compute average intra-cluster correlation
            intra_corrs = []
            for i_idx in range(len(member_symbols)):
                for j_idx in range(i_idx + 1, len(member_symbols)):
                    pair = (member_symbols[i_idx], member_symbols[j_idx])
                    rev_pair = (member_symbols[j_idx], member_symbols[i_idx])
                    c = corr_lookup.get(pair) or corr_lookup.get(rev_pair)
                    if c is not None:
                        intra_corrs.append(c)
            avg_corr = float(np.mean(intra_corrs)) if intra_corrs else 0.0

            # Lead coin = highest average pairwise correlation within cluster
            member_changes = {s: change_map.get(s, 0.0) for s in member_symbols}
            lead_symbol = None
            lead_avg_corr = -1.0
            for s in member_symbols:
                others = [o for o in member_symbols if o != s]
                if not others:
                    continue
                s_corrs = []
                for o in others:
                    pair = tuple(sorted([s, o]))
                    c = corr_lookup.get(pair) or corr_lookup.get((pair[1], pair[0]))
                    if c is not None:
                        s_corrs.append(c)
                if s_corrs:
                    avg = float(np.mean(s_corrs))
                    if avg > lead_avg_corr:
                        lead_avg_corr = avg
                        lead_symbol = s
            if not lead_symbol:
                lead_symbol = member_symbols[0]
            lead_change = member_changes.get(lead_symbol, 0.0)

            # Strength = coin_count * avg_corr * avg_abs_change
            avg_abs_change = float(np.mean([abs(member_changes.get(s, 0)) for s in member_symbols]))
            strength = coin_count * avg_corr * avg_abs_change

            # Use a placeholder avg_high_time (midnight UTC of target date)
            # v2 doesn't use time-based clustering but the column is NOT NULL
            avg_high_time = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)

            cur.execute(
                """
                INSERT INTO dynamic_theme_cluster
                    (created_date, coin_count, strength_score, avg_high_time,
                     time_spread_minutes, avg_high_change_pct,
                     lead_symbol, lead_change_pct, avg_correlation)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING cluster_id
                """,
                (
                    target_date, coin_count, round(strength, 4), avg_high_time,
                    0.0,  # time_spread not used in v2
                    round(avg_abs_change, 4),
                    lead_symbol, round(lead_change, 4), round(avg_corr, 4),
                ),
            )
            cluster_id = cur.fetchone()[0]

            # Insert members
            for s in member_symbols:
                chg = member_changes.get(s, 0.0)
                # Correlation to lead
                if s == lead_symbol:
                    corr_to_lead = 1.0
                else:
                    pair_key = tuple(sorted([s, lead_symbol]))
                    corr_to_lead = corr_lookup.get(pair_key, corr_lookup.get((pair_key[1], pair_key[0]), 0.0))

                cur.execute(
                    """
                    INSERT INTO dynamic_theme_member
                        (cluster_id, symbol, high_time, high_price, high_change_pct,
                         daily_change_pct, correlation_to_lead)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        cluster_id, s, avg_high_time, 0.0, abs(chg),
                        round(chg, 4), round(corr_to_lead, 4),
                    ),
                )

            logger.info(
                f"Cluster {cluster_id}: {coin_count} coins, lead={lead_symbol} ({lead_change:+.2f}%), "
                f"avg_corr={avg_corr:.3f}, strength={strength:.2f}"
            )

        conn.commit()
        logger.info(f"Clustering complete for {target_date}")

    except Exception as e:
        logger.error(f"build_clusters failed: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


with DAG(
    "dynamic_theme_discovery",
    default_args=default_args,
    description="Discover dynamic themes via market-neutral Agglomerative clustering (daily)",
    schedule_interval="0 21 * * *",
    catchup=False,
    tags=["theme", "analysis", "trade"],
) as dag:

    compute_task = PythonOperator(
        task_id="compute_daily_correlation",
        python_callable=compute_daily_correlation,
    )

    cluster_task = PythonOperator(
        task_id="build_clusters",
        python_callable=build_clusters,
    )

    compute_task >> cluster_task
