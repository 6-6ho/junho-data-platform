#!/bin/bash
# Backfill Timeseries Performance Analysis
# Run this script on Desktop node

set -e

echo "====================================="
echo "Timeseries Performance Backfill"
echo "====================================="

# Check if running on Desktop
if ! docker ps | grep -q jdp-airflow; then
    echo "ERROR: This script should run on Desktop node"
    echo "Please run: ssh <DESKTOP_HOST> 'cd ~/junho-data-platform && ./run_backfill_timeseries.sh'"
    exit 1
fi

# Set environment variables
export DB_HOST=${LAPTOP_IP:-localhost}
export POSTGRES_PASSWORD=postgres
export DAYS_BACK=7

echo "Configuration:"
echo "  DB_HOST: $DB_HOST (Laptop PostgreSQL)"
echo "  DAYS_BACK: $DAYS_BACK days"
echo ""

# Run backfill script using Python
docker run --rm \
    --network jdp_appnet \
    -e DB_HOST=$DB_HOST \
    -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
    -v $(pwd)/spark/jobs:/app/jobs:ro \
    python:3.11-slim \
    bash -c "
        pip install -q psycopg2-binary requests &&
        cd /app/jobs/trade &&
        python3 backfill_timeseries_performance.py
    "

echo ""
echo "====================================="
echo "Backfill Complete!"
echo "====================================="
echo ""
echo "Check results:"
echo "  docker exec jdp-shop-api python3 -c \"import psycopg2; conn=psycopg2.connect(host='\$DB_HOST',port=5432,database='app',user='postgres',password='\$POSTGRES_PASSWORD'); cur=conn.cursor(); cur.execute('SELECT COUNT(*) FROM trade_performance_timeseries'); print('Total timeseries records:', cur.fetchone()[0])\""
