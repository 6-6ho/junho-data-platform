#!/bin/bash
# Full Timeseries Performance Backfill
# Processes all [Large] Rise signals from last 7 days

echo "======================================"
echo "Full Timeseries Backfill (7 days)"
echo "======================================"
echo ""
echo "⚠️  This will process ~600 signals"
echo "    Estimated time: ~15 minutes"
echo ""
read -p "Continue? (y/N): " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

docker exec jdp-shop-api bash -c "
apt-get update -qq && apt-get install -y -qq curl > /dev/null 2>&1 || true

cat > /tmp/backfill_full.py << 'PYEOF'
import os, time, json, subprocess, psycopg2
from datetime import datetime, timezone

BINANCE_API = 'https://fapi.binance.com'
WIN_THRESHOLD_PCT = 1.0
RATE_LIMIT_SLEEP = 0.15
DB_CONFIG = {'host': '192.168.219.101', 'port': 5432, 'dbname': 'app', 'user': 'postgres', 'password': 'postgres'}

def curl_get(url):
    r = subprocess.run(['curl', '-s', '--connect-timeout', '10', url], capture_output=True, text=True, timeout=20)
    return json.loads(r.stdout)

def fetch_klines(symbol, start_time_ms, interval='5m', limit=100):
    url = f'{BINANCE_API}/fapi/v1/klines?symbol={symbol}&interval={interval}&startTime={start_time_ms}&limit={limit}'
    try:
        klines = curl_get(url)
        return klines if not isinstance(klines, dict) else []
    except: return []

def analyze_timeseries_performance(symbol, alert_time_ms, entry_price):
    klines = fetch_klines(symbol, alert_time_ms, interval='5m', limit=49)
    if not klines or len(klines) < 2: return None
    future_candles, timeseries_data = klines[1:], {}
    for interval_minutes in range(5, 245, 5):
        candle_idx = (interval_minutes // 5) - 1
        if candle_idx >= len(future_candles): break
        close_price = float(future_candles[candle_idx][4])
        profit_pct = ((close_price - entry_price) / entry_price) * 100
        timeseries_data[str(interval_minutes)] = {'price': round(close_price, 8), 'profit_pct': round(profit_pct, 4), 'is_win': profit_pct >= WIN_THRESHOLD_PCT}
    return {'timeseries_data': timeseries_data} if timeseries_data else None

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()
cur.execute('''
    SELECT DISTINCT symbol, type, event_time, change_pct_window
    FROM movers_latest
    WHERE event_time >= NOW() - INTERVAL '7 days' AND type = 'rise' AND change_pct_window >= 5.0
      AND NOT EXISTS (SELECT 1 FROM trade_performance_timeseries ts WHERE ts.symbol = movers_latest.symbol AND ts.alert_time = movers_latest.event_time)
    ORDER BY event_time DESC
''')
signals = cur.fetchall()
print(f'Processing {len(signals)} signals...')
processed, skipped, errors, t0 = 0, 0, 0, time.time()

for i, (symbol, alert_type, event_time, change_pct) in enumerate(signals):
    try:
        alert_time_ms = int(event_time.timestamp() * 1000)
        klines = fetch_klines(symbol, alert_time_ms, interval='5m', limit=1)
        if not klines: skipped += 1; time.sleep(RATE_LIMIT_SLEEP); continue
        entry_price = float(klines[0][4])
        ts_result = analyze_timeseries_performance(symbol, alert_time_ms, entry_price)
        if ts_result:
            cur.execute('''INSERT INTO trade_performance_timeseries (symbol, alert_type, alert_time, entry_price, timeseries_data)
                           VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING''',
                        (symbol, alert_type, event_time, entry_price, json.dumps(ts_result['timeseries_data'])))
            conn.commit(); processed += 1
            if (i+1) % 50 == 0 or i == 0:
                elapsed, rate = time.time() - t0, (i+1) / max(time.time() - t0, 1)
                eta = (len(signals) - i - 1) / rate if rate > 0 else 0
                print(f'[{i+1}/{len(signals)}] {symbol}: OK | ETA: {eta/60:.1f}min | P:{processed} S:{skipped} E:{errors}')
        else: skipped += 1
        time.sleep(RATE_LIMIT_SLEEP)
    except Exception as e:
        print(f'[{i+1}] ERROR {symbol}: {e}')
        conn.rollback(); errors += 1; time.sleep(0.5)

conn.commit(); cur.close(); conn.close()
elapsed = time.time() - t0
print(f'\nDONE in {elapsed/60:.1f}min | Processed:{processed} Skipped:{skipped} Errors:{errors}')
PYEOF

python3 /tmp/backfill_full.py
"

echo ""
echo "======================================"
echo "Backfill Complete!"
echo "Check: docker exec jdp-shop-api python3 -c \"import psycopg2; conn=psycopg2.connect(host='192.168.219.101',port=5432,database='app',user='postgres',password='postgres'); cur=conn.cursor(); cur.execute('SELECT COUNT(*) FROM trade_performance_timeseries'); print('Total records:', cur.fetchone()[0])\""
echo "======================================"
