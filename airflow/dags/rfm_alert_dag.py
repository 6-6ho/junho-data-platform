"""
RFM Risk Alert DAG

Runs after user_rfm_dag (04:00 UTC daily).
Checks mart_user_rfm for segment distribution and sends Telegram alert
when Risk ratio > 30% or VIP ratio < 5%.
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os


default_args = {
    'owner': 'junho',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

LAPTOP_IP = os.getenv("LAPTOP_IP", "postgres")


def check_rfm_and_alert():
    import psycopg2
    import urllib.request
    import json

    db_host = os.getenv("LAPTOP_IP", "postgres")
    conn = psycopg2.connect(
        host=db_host,
        port=5432,
        database="app",
        user="postgres",
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE rfm_segment = 'Risk')  AS risk_count,
            COUNT(*) FILTER (WHERE rfm_segment = 'VIP')   AS vip_count,
            COUNT(*)                                       AS total
        FROM mart_user_rfm
    """)
    risk_count, vip_count, total = cur.fetchone()
    cur.close()
    conn.close()

    if total == 0:
        print("No RFM data yet. Skipping alert.")
        return

    risk_ratio = risk_count / total
    vip_ratio = vip_count / total

    print(f"RFM Distribution — Total: {total}, Risk: {risk_count} ({risk_ratio:.1%}), VIP: {vip_count} ({vip_ratio:.1%})")

    alerts = []
    if risk_ratio > 0.30:
        alerts.append(f"Risk 고객 비율 {risk_ratio:.1%} (임계치 30% 초과) — 윈백 캠페인 필요")
    if vip_ratio < 0.05:
        alerts.append(f"VIP 고객 비율 {vip_ratio:.1%} (임계치 5% 미만) — 리텐션 전략 점검 필요")

    if not alerts:
        print("RFM segments within healthy thresholds.")
        return

    # Send Telegram alert
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("Telegram credentials not configured. Printing alert only.")
        for a in alerts:
            print(f"[ALERT] {a}")
        return

    message = "[RFM Alert]\n" + "\n".join(alerts)
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": message}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
        print("Telegram alert sent.")
    except Exception as e:
        print(f"Telegram send failed: {e}")


with DAG(
    'rfm_alert_dag',
    default_args=default_args,
    description='Check RFM segment ratios and alert on Risk/VIP anomalies',
    schedule_interval='0 4 * * *',  # Daily at 04:00 UTC (13:00 KST), after user_rfm_dag
    catchup=False,
    tags=['shop', 'alert', 'rfm'],
) as dag:

    check_and_alert = PythonOperator(
        task_id='check_rfm_segments',
        python_callable=check_rfm_and_alert,
    )
