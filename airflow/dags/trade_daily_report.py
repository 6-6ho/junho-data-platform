from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import pandas as pd
import requests
import os
import time
import json

# Config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

default_args = {
    'owner': 'junho',
    'depends_on_past': False,
    'start_date': datetime(2023, 10, 1),
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN:
        print("Telegram token missing")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True 
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send telegram: {e}")

def fetch_binance_klines(symbol, start_time_ms, limit=30):
    """
    Fetch 5m klines from Binance Futures starting from start_time_ms.
    Returns list of [timestamp, open, high, low, close, volume, ...]
    """
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {
        "symbol": symbol,
        "interval": "5m",
        "startTime": start_time_ms,
        "limit": limit
    }
    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Binance API error for {symbol}: {e}")
        return []

def analyze_post_alert_performance(engine):
    """
    Analyze performance of Pump alerts in the last 24h.
    Strategy: Buy at Close of Alert Candle -> Hold 30 candles (2.5h) -> Check Max Profit
    """
    print("Starting Post-Alert Analysis...")
    
    # 1. Get recent Pump alerts
    query = """
    SELECT symbol, event_time, change_pct_window
    FROM mart_movers
    WHERE type = 'Pump' 
      AND event_time >= NOW() - INTERVAL '24 hours'
      AND event_time <= NOW() - INTERVAL '3 hours' -- Ensure we have 2.5h of data
    ORDER BY event_time DESC
    """
    try:
        alerts = pd.read_sql(query, engine)
    except Exception as e:
        print(f"DB Error: {e}")
        return None

    if alerts.empty:
        return None

    results = []
    
    for _, row in alerts.iterrows():
        symbol = row['symbol']
        # Convert timestamp to ms
        event_ts = int(row['event_time'].timestamp() * 1000)
        
        # Determine strict start time for proper backtest:
        # If 'event_time' is the time alert triggered, we assume we enter at that moment (or close of that minute).
        # To be safe, let's fetch klines starting from that event time.
        # Note: Binance API 'startTime' is inclusive.
        
        klines = fetch_binance_klines(symbol, event_ts, limit=31) 
        # We need at least 2 candles (Entry + Next)
        if not klines or len(klines) < 5: 
            continue
            
        # klines[0] is the candle where alert happened (or close to it). 
        # Let's assume Entry Price = Close of klines[0] (Conservative)
        entry_price = float(klines[0][4])
        
        # Analyze subsequent candles (up to 30)
        max_price = entry_price
        final_price = float(klines[-1][4])
        
        future_candles = klines[1:] # Candles after entry
        if not future_candles:
            continue
            
        for k in future_candles:
            high = float(k[2])
            if high > max_price:
                max_price = high
                
        max_profit_pct = ((max_price - entry_price) / entry_price) * 100
        final_profit_pct = ((final_price - entry_price) / entry_price) * 100
        
        results.append({
            "symbol": symbol,
            "max_profit": max_profit_pct,
            "final_profit": final_profit_pct
        })
        time.sleep(0.1) # Rate limit protection

    if not results:
        return None
        
    df_res = pd.DataFrame(results)
    
    # Metrics
    avg_max_profit = df_res['max_profit'].mean()
    win_rate = len(df_res[df_res['max_profit'] > 1.0]) / len(df_res) * 100 # Win if Max Profit > 1%
    
    best_trade = df_res.loc[df_res['max_profit'].idxmax()]
    
    return {
        "count": len(df_res),
        "avg_max_profit": avg_max_profit,
        "win_rate": win_rate,
        "best_symbol": best_trade['symbol'],
        "best_profit": best_trade['max_profit']
    }

def generate_report(**context):
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    engine = pg_hook.get_sqlalchemy_engine()
    
    # 1. DQ Check (Last 24h)
    dq_query = """
    SELECT 
        COUNT(*) as total_minutes,
        SUM(total_volume) as day_volume,
        MIN(window_start) as start_time,
        MAX(window_end) as end_time
    FROM mart_trade_stats
    WHERE window_start >= NOW() - INTERVAL '24 hours'
    """
    dq_df = pd.read_sql(dq_query, engine)
    
    total_minutes = dq_df.iloc[0]['total_minutes'] if not dq_df.empty else 0
    day_volume = dq_df.iloc[0]['day_volume']
    if day_volume is None:
        day_volume = 0.0
    
    # Target: 1440 mins
    availability = (total_minutes / 1440.0) * 100
    if availability > 100: availability = 100.0
    
    # 2. Pump Pattern EDA (Last 24h)
    pattern_query = """
    SELECT 
        symbol, 
        COUNT(*) as pump_count,
        AVG(change_pct_window) as avg_change
    FROM mart_movers
    WHERE event_time >= NOW() - INTERVAL '24 hours'
    GROUP BY symbol
    ORDER BY pump_count DESC
    LIMIT 3
    """
    top_movers = pd.read_sql(pattern_query, engine)
    
    # 3. Hourly Distribution
    hour_query = """
    SELECT 
        EXTRACT(HOUR FROM event_time) as hour_of_day,
        COUNT(*) as cnt
    FROM mart_movers
    WHERE event_time >= NOW() - INTERVAL '24 hours'
    GROUP BY 1
    ORDER BY 2 DESC
    LIMIT 1
    """
    peak_hour_df = pd.read_sql(hour_query, engine)
    peak_hour = int(peak_hour_df.iloc[0]['hour_of_day']) if not peak_hour_df.empty else -1
    
    # 4. Post-Alert Analysis (New)
    analysis_stats = analyze_post_alert_performance(engine)
    
    # 5. Construct Message
    report = f"📊 *Daily Trade Report (Last 24h)*\n\n"
    
    # QA Section
    icon_dq = "✅" if availability > 95 else "⚠️"
    report += f"*Data Quality {icon_dq}*\n"
    report += f"- Availability: *{availability:.1f}%* ({total_minutes}/1440 mins)\n"
    report += f"- Total Vol (Est): {day_volume:,.0f}\n\n"
    
    # Insight Section
    report += f"*Market Insights*\n"
    if not top_movers.empty:
        movers_str = ", ".join([f"{r.symbol}({r.pump_count})" for _, r in top_movers.iterrows()])
        report += f"- 🔥 Top Movers: {movers_str}\n"
    else:
        report += f"- 🔥 Top Movers: None\n"
        
    if peak_hour != -1:
        report += f"- ⏰ Peak Hour: *{peak_hour}:00 ~ {peak_hour+1}:00* (KST)\n"

    # Analysis Section (New)
    if analysis_stats:
        win_rate = analysis_stats['win_rate']
        icon_perf = "🚀" if win_rate > 50 else "📉"
        report += f"\n*Signal Accuracy (2.5h hold)* {icon_perf}\n"
        report += f"- Analyzed Signals: {analysis_stats['count']}\n"
        report += f"- Win Rate (>1%): *{win_rate:.1f}%*\n"
        report += f"- Avg Max Return: *{analysis_stats['avg_max_profit']:.2f}%*\n"
        report += f"- Best Setup: {analysis_stats['best_symbol']} (+{analysis_stats['best_profit']:.1f}%)\n"
    
    # Link
    report_link = f"https://trade.6-6ho.com/reports?date={datetime.now().strftime('%Y-%m-%d')}"
    report += f"\n[📊 View Full Dashboard]({report_link})\n"
    report += f"\n_Generated by Airflow_"
    
    # Send
    send_telegram(report)
    
    # Archive for RAG/Web
    current_date = datetime.now().strftime('%Y-%m-%d')
    archive_query = """
    INSERT INTO report_archive (report_date, report_type, content)
    VALUES (%s, 'daily_trade', %s)
    """
    try:
        conn = pg_hook.get_conn()
        cur = conn.cursor()
        cur.execute(archive_query, (current_date, report))
        conn.commit()
        print("Report archived successfully")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Failed to archive report: {e}")
        
    return "Report Sent & Archived"

with DAG(
    'trade_daily_report',
    default_args=default_args,
    description='Daily Trade DQ and EDA Report',
    schedule_interval='0 0 * * *', # Daily at 00:00 UTC (09:00 KST)
    catchup=False
) as dag:

    t1 = PythonOperator(
        task_id='generate_and_send_report',
        python_callable=generate_report
    )
