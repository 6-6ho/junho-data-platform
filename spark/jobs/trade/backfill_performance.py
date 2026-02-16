"""
Backfill Script: Detect movers from Binance Klines and analyze performance.
Uses curl (subprocess) for Binance API calls to bypass Python SSL issues.
"""
import os
import time
import json
import subprocess
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone

BINANCE_API = "https://fapi.binance.com"
THRESHOLD_5M = 3.0
WIN_THRESHOLD = 1.0
STOP_LOSS = -2.0
ANALYSIS_WINDOWS = [60, 240]
DAYS_BACK = 7
RATE_LIMIT_SLEEP = 0.12

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "postgres"),
    "port": 5432,
    "dbname": "app",
    "user": "postgres",
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
}


def curl_get(url):
    r = subprocess.run(["curl", "-s", "--connect-timeout", "10", url],
                       capture_output=True, text=True, timeout=20)
    return json.loads(r.stdout)


def get_usdt_perps():
    data = curl_get(f"{BINANCE_API}/fapi/v1/exchangeInfo")
    return sorted([
        s['symbol'] for s in data['symbols']
        if s['contractType'] == 'PERPETUAL'
        and s['quoteAsset'] == 'USDT'
        and s['status'] == 'TRADING'
    ])


def fetch_klines(symbol, start_ms, end_ms):
    all_klines = []
    cur_start = start_ms
    while cur_start < end_ms:
        url = (f"{BINANCE_API}/fapi/v1/klines?"
               f"symbol={symbol}&interval=5m&startTime={cur_start}"
               f"&endTime={end_ms}&limit=1500")
        try:
            klines = curl_get(url)
            if not klines or isinstance(klines, dict):
                break
            all_klines.extend(klines)
            cur_start = klines[-1][0] + 1
            if len(klines) < 1500:
                break
            time.sleep(RATE_LIMIT_SLEEP)
        except Exception as e:
            print(f"  API err: {e}")
            time.sleep(1)
            break
    return all_klines


def detect_and_analyze(symbol, klines):
    movers, perfs = [], []
    last_t = 0
    for i in range(len(klines)):
        op, cp = float(klines[i][1]), float(klines[i][4])
        t_ms = klines[i][0]
        if op == 0:
            continue
        chg = ((cp - op) / op) * 100
        if chg < THRESHOLD_5M or t_ms - last_t < 300000:
            continue
        last_t = t_ms
        at = datetime.fromtimestamp(t_ms / 1000, tz=timezone.utc)
        st = "[Large] Rise" if chg >= 5.0 else "[Small] Rise"
        movers.append({"type":"rise","symbol":symbol,"status":st,"window":"5m",
                       "event_time":at,"change_pct_window":round(chg,4),
                       "change_pct_24h":0.0,"vol_ratio":0.0})
        entry = cp
        for wm in ANALYSIS_WINDOWS:
            nc = wm // 5
            fut = klines[i+1:i+1+nc]
            if len(fut) < 3:
                continue
            mx, mn = entry, entry
            for k in fut:
                h, l = float(k[2]), float(k[3])
                if h > mx: mx = h
                if l < mn: mn = l
            cf = float(fut[-1][4])
            mp = ((mx-entry)/entry)*100
            md = ((mn-entry)/entry)*100
            fp = ((cf-entry)/entry)*100
            iw = mp >= WIN_THRESHOLD
            rt = "WIN" if iw else ("LOSS" if md <= STOP_LOSS else "BREAK_EVEN")
            perfs.append({"symbol":symbol,"alert_type":"rise","alert_time":at,
                          "window_min":wm,"entry_price":entry,"max_price":mx,
                          "min_price":mn,"close_price":cf,
                          "max_profit_pct":round(mp,4),"max_drawdown_pct":round(md,4),
                          "final_profit_pct":round(fp,4),"is_win":iw,"result_type":rt})
    return movers, perfs


def main():
    print("="*60)
    print(f"Backfill: Last {DAYS_BACK} days | Threshold: {THRESHOLD_5M}%")
    print("="*60, flush=True)

    symbols = get_usdt_perps()
    print(f"Found {len(symbols)} USDT perps", flush=True)

    end_ms = int(time.time() * 1000)
    start_ms = end_ms - (DAYS_BACK * 24 * 60 * 60 * 1000)
    print(f"Range: {datetime.fromtimestamp(start_ms/1000,tz=timezone.utc):%m/%d %H:%M} ~ "
          f"{datetime.fromtimestamp(end_ms/1000,tz=timezone.utc):%m/%d %H:%M} UTC", flush=True)

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    tm, tp, errs = 0, 0, 0

    m_sql = """INSERT INTO movers_latest (type,symbol,status,"window",event_time,
               change_pct_window,change_pct_24h,vol_ratio,updated_at)
               VALUES %s ON CONFLICT (type,symbol,status,event_time) DO NOTHING"""
    p_sql = """INSERT INTO trade_performance (symbol,alert_type,alert_time,
               analysis_window_minutes,entry_price,max_price,min_price,close_price,
               max_profit_pct,max_drawdown_pct,final_profit_pct,is_win,result_type)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""

    t0 = time.time()
    for i, sym in enumerate(symbols):
        try:
            kl = fetch_klines(sym, start_ms, end_ms)
            if not kl: continue
            mvs, pfs = detect_and_analyze(sym, kl)
            if mvs:
                d = [(m['type'],m['symbol'],m['status'],m['window'],m['event_time'],
                      m['change_pct_window'],m['change_pct_24h'],m['vol_ratio'],
                      datetime.now(timezone.utc)) for m in mvs]
                psycopg2.extras.execute_values(cur, m_sql, d)
                tm += len(mvs)
            for p in pfs:
                cur.execute(p_sql,(p['symbol'],p['alert_type'],p['alert_time'],
                    p['window_min'],p['entry_price'],p['max_price'],p['min_price'],
                    p['close_price'],p['max_profit_pct'],p['max_drawdown_pct'],
                    p['final_profit_pct'],p['is_win'],p['result_type']))
                tp += 1
            conn.commit()
            if mvs:
                print(f"[{i+1}/{len(symbols)}] {sym}: {len(mvs)}m {len(pfs)}p", flush=True)
            time.sleep(RATE_LIMIT_SLEEP)
        except Exception as e:
            print(f"[{i+1}/{len(symbols)}] ERR {sym}: {e}", flush=True)
            conn.rollback(); errs += 1; time.sleep(0.5)
        if (i+1) % 100 == 0:
            elapsed = time.time() - t0
            rate = (i+1) / elapsed if elapsed > 0 else 0
            eta = (len(symbols) - i - 1) / rate if rate > 0 else 0
            print(f"\n--- {i+1}/{len(symbols)} | M:{tm} P:{tp} E:{errs} | "
                  f"ETA:{eta/60:.1f}min ---\n", flush=True)

    conn.commit(); cur.close(); conn.close()
    elapsed = time.time() - t0
    print(f"\n{'='*60}\nDONE in {elapsed/60:.1f}min | Movers:{tm} Perf:{tp} Errors:{errs}\n{'='*60}")


if __name__ == "__main__":
    main()
