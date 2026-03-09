#!/bin/bash
# Backfill dynamic theme correlation data from 2026-01-01 to yesterday
# Usage: ./scripts/backfill_dynamic_theme.sh [start_date] [end_date]
#   defaults: start=2026-01-01, end=yesterday

set -euo pipefail

START_DATE="${1:-2026-01-01}"
END_DATE="${2:-$(date -u -d 'yesterday' +%Y-%m-%d)}"

echo "=== Dynamic Theme v3 Backfill (market-neutral) ==="
echo "Range: $START_DATE ~ $END_DATE"
echo "Note: First 14 days build correlation only. Clusters start from day 15."
echo ""

current="$START_DATE"
count=0
total=$(( ($(date -d "$END_DATE" +%s) - $(date -d "$START_DATE" +%s)) / 86400 + 1 ))

while [[ "$current" < "$END_DATE" ]] || [[ "$current" == "$END_DATE" ]]; do
    count=$((count + 1))
    echo "[$count/$total] Triggering for $current ..."

    docker exec jdp-airflow-scheduler-1 airflow dags trigger \
        -c "{\"ds\": \"$current\"}" \
        dynamic_theme_discovery 2>/dev/null || {
        echo "  WARN: trigger failed for $current, continuing..."
    }

    # Wait for scheduler to pick it up
    sleep 5

    current=$(date -d "$current + 1 day" +%Y-%m-%d)
done

echo ""
echo "=== Backfill triggered: $count days ==="
echo "Monitor: docker exec jdp-airflow-scheduler-1 airflow dags list-runs -d dynamic_theme_discovery"
