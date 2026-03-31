from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json
import logging
import jwt
from kafka import KafkaProducer

logger = logging.getLogger(__name__)

app = FastAPI(title="Shop Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use /api prefix to match existing frontend proxy
router = APIRouter(prefix="/api/analytics", tags=["analytics"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])

# --- Setup Kafka Producer ---
try:
    producer = KafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        key_serializer=lambda k: k.encode('utf-8') if k else None,
        retries=3
    )
except Exception as e:
    print(f"Warning: Could not connect to Kafka: {e}")
    producer = None

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

class LoginRequest(BaseModel):
    password: str

class GeneratorSettingsUpdate(BaseModel):
    mode: str
    base_tps: int
    chaos_mode: bool
    category_bias: Optional[str] = None
    user_persona_bias: Optional[str] = None
    duration_minutes: Optional[int] = None # Time-bound execution

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("POSTGRES_DB", "app"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres")
    )

def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/")
def read_root():
    return {"status": "ok", "service": "shop-backend"}

@router.get("/summary")
async def get_summary():
    """파이프라인 개요 + DoD 비교 (mart_daily_summary 활용)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 24h 집계 (speed layer)
        cur.execute("""
            SELECT COALESCE(SUM(event_count),0), COALESCE(SUM(total_revenue),0)
            FROM dq_category_hourly WHERE hour >= NOW() - INTERVAL '24 hours'
        """)
        row = cur.fetchone()
        today_events = int(row[0] or 0)
        today_revenue = float(row[1] or 0)

        # Total events approximate
        cur.execute("SELECT reltuples::bigint FROM pg_class WHERE relname = 'dq_category_hourly'")
        total_events = int(cur.fetchone()[0] or 0)

        # Data freshness
        cur.execute("SELECT EXTRACT(EPOCH FROM (NOW()-created_at)) FROM shop_hourly_sales_log ORDER BY created_at DESC LIMIT 1")
        fr = cur.fetchone()
        data_freshness_sec = int(fr[0]) if fr and fr[0] else None

        # DoD 비교: mart_daily_summary 최근 2일
        cur.execute("SELECT date,total_revenue,total_orders,avg_order_value,top_category FROM mart_daily_summary ORDER BY date DESC LIMIT 2")
        mart = cur.fetchall()
        avg_order_value = float(mart[0][3]) if mart and mart[0][3] else None
        top_category = mart[0][4] if mart else None
        dod_revenue_pct = None
        dod_orders_pct = None
        if len(mart) >= 2:
            cr, pr = float(mart[0][1]), float(mart[1][1])
            co, po = int(mart[0][2]), int(mart[1][2])
            if pr > 0:
                dod_revenue_pct = round((cr - pr) / pr * 100, 1)
            if po > 0:
                dod_orders_pct = round((co - po) / po * 100, 1)

        cur.close()
        conn.close()
        return {
            "total_events": total_events, "today_events": today_events,
            "today_revenue": round(today_revenue, 0), "data_freshness_sec": data_freshness_sec,
            "avg_order_value": avg_order_value, "top_category": top_category,
            "dod_revenue_pct": dod_revenue_pct, "dod_orders_pct": dod_orders_pct,
        }
    except Exception as e:
        logger.error(f"summary failed: {e}")
        return {
            "total_events": 0, "today_events": 0, "today_revenue": 0,
            "data_freshness_sec": None, "avg_order_value": None, "top_category": None,
            "dod_revenue_pct": None, "dod_orders_pct": None, "error": str(e),
        }

@router.get("/hourly-traffic")
async def get_hourly_traffic():
    """카테고리별 시간대 트래픽 (shop_hourly_sales_log 기반)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                window_start + INTERVAL '9 hours' AS window_start_kst,
                category,
                COALESCE(SUM(order_count), 0) as count
            FROM shop_hourly_sales_log
            WHERE window_start >= NOW() - INTERVAL '24 hours'
            GROUP BY window_start_kst, category
            ORDER BY window_start_kst
        """)

        rows = cur.fetchall()
        # Pivot: group by window_start, each category becomes a key
        from collections import OrderedDict
        pivoted = OrderedDict()
        for r in rows:
            ts = r[0].isoformat() if hasattr(r[0], 'isoformat') else str(r[0])
            if ts not in pivoted:
                pivoted[ts] = {"time": ts}
            pivoted[ts][r[1]] = int(r[2])

        result = list(pivoted.values())

        cur.close()
        conn.close()

        return result
    except Exception as e:
        logger.error(f"hourly-traffic failed: {e}")
        return []

@router.get("/hourly-throughput")
async def get_hourly_throughput():
    """시간별 총 처리량 추이 (파이프라인 가동 현황)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                window_start + INTERVAL '9 hours' AS hour,
                SUM(order_count) AS total_orders
            FROM shop_hourly_sales_log
            WHERE window_start >= NOW() - INTERVAL '24 hours'
            GROUP BY hour
            ORDER BY hour
        """)

        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append({
                "hour": r[0].isoformat() if hasattr(r[0], 'isoformat') else str(r[0]),
                "total_orders": int(r[1])
            })

        cur.close()
        conn.close()

        return result
    except Exception as e:
        logger.error(f"hourly-throughput failed: {e}")
        return []

@router.get("/funnel")
async def get_funnel():
    """퍼널 분석"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                COALESCE(SUM(view_count), 100) as page_view,
                COALESCE(SUM(cart_count), 25) as add_to_cart,
                COALESCE(SUM(purchase_count), 3) as purchase
            FROM shop_funnel_stats_log
        """)
        
        row = cur.fetchone()
        pv = row[0] or 100
        atc = row[1] or 25
        purchase = row[2] or 3
        
        cur.close()
        conn.close()
        
        return {
            "page_view": int(pv),
            "add_to_cart": int(atc),
            "purchase": int(purchase),
            "conversion_rate": round(purchase / pv * 100, 2) if pv > 0 else 0
        }
    except Exception as e:
        logger.error(f"funnel failed: {e}")
        return {
            "page_view": 0,
            "add_to_cart": 0,
            "purchase": 0,
            "conversion_rate": 0
        }

@router.get("/dq/score-trend")
async def get_dq_score_trend():
    """DQ 일별 스코어 트렌드 (최근 14일)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT date, completeness_score, validity_score, timeliness_score, total_score
            FROM dq_daily_score
            ORDER BY date DESC
            LIMIT 14
        """)
        rows = cur.fetchall()
        for r in rows:
            r['date'] = r['date'].isoformat() if hasattr(r['date'], 'isoformat') else str(r['date'])
        cur.close()
        conn.close()
        return list(reversed(rows))
    except Exception as e:
        logger.error(f"dq/score-trend failed: {e}")
        return []

@router.get("/dq/anomalies")
async def get_dq_anomalies():
    """DQ 이상 감지 로그 (최근 20건)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT
                detected_at AT TIME ZONE 'Asia/Seoul' AS detected_at,
                anomaly_type, dimension,
                expected_value, actual_value, severity, notes
            FROM dq_anomaly_log
            ORDER BY detected_at DESC
            LIMIT 20
        """)
        rows = cur.fetchall()
        for r in rows:
            r['detected_at'] = r['detected_at'].isoformat() if hasattr(r['detected_at'], 'isoformat') else str(r['detected_at'])
            r['expected_value'] = float(r['expected_value']) if r['expected_value'] is not None else None
            r['actual_value'] = float(r['actual_value']) if r['actual_value'] is not None else None
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"dq/anomalies failed: {e}")
        return []

@router.get("/dq/category-health")
async def get_dq_category_health():
    """카테고리별 건강도 (최근 24시간)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT category, SUM(event_count) as event_count,
                   SUM(purchase_count) as purchase_count,
                   SUM(total_revenue) as total_revenue
            FROM dq_category_hourly
            WHERE hour >= NOW() - INTERVAL '24 hours'
            GROUP BY category
            ORDER BY event_count DESC
        """)
        rows = cur.fetchall()
        for r in rows:
            r['event_count'] = int(r['event_count'])
            r['purchase_count'] = int(r['purchase_count'])
            r['total_revenue'] = float(r['total_revenue'])
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"dq/category-health failed: {e}")
        return []

@router.get("/dq/payment-health")
async def get_dq_payment_health():
    """결제수단별 건강도 (최근 24시간)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT payment_method, SUM(purchase_count) as purchase_count,
                   SUM(total_revenue) as total_revenue
            FROM dq_payment_hourly
            WHERE hour >= NOW() - INTERVAL '24 hours'
            GROUP BY payment_method
            ORDER BY purchase_count DESC
        """)
        rows = cur.fetchall()
        for r in rows:
            r['purchase_count'] = int(r['purchase_count'])
            r['total_revenue'] = float(r['total_revenue'])
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"dq/payment-health failed: {e}")
        return []

@router.get("/dq/reconciliation")
async def get_dq_reconciliation():
    """파이프라인 정합성 검증 — category_hourly vs payment_hourly 시간별 교차 검증"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            WITH cat AS (
                SELECT hour AT TIME ZONE 'Asia/Seoul' AS hour_kst, SUM(purchase_count) AS total
                FROM dq_category_hourly
                WHERE hour >= NOW() - INTERVAL '24 hours'
                GROUP BY hour_kst
            ),
            pay AS (
                SELECT hour AT TIME ZONE 'Asia/Seoul' AS hour_kst, SUM(purchase_count) AS total
                FROM dq_payment_hourly
                WHERE hour >= NOW() - INTERVAL '24 hours'
                GROUP BY hour_kst
            )
            SELECT
                COALESCE(c.hour_kst, p.hour_kst) AS hour,
                COALESCE(c.total, 0) AS category_total,
                COALESCE(p.total, 0) AS payment_total
            FROM cat c
            FULL OUTER JOIN pay p ON c.hour_kst = p.hour_kst
            ORDER BY hour
        """)
        rows = cur.fetchall()
        result = []
        for r in rows:
            hr, cat_total, pay_total = r
            cat_total = int(cat_total)
            pay_total = int(pay_total)
            base = max(cat_total, pay_total, 1)
            diff_pct = abs(cat_total - pay_total) / base * 100
            result.append({
                "hour": hr.isoformat() if hasattr(hr, 'isoformat') else str(hr),
                "category_total": cat_total,
                "payment_total": pay_total,
                "diff_pct": round(diff_pct, 1)
            })
        cur.close()
        conn.close()
        return result
    except Exception as e:
        logger.error(f"dq/reconciliation failed: {e}")
        return []

@router.get("/dq/rules-summary")
async def get_dq_rules_summary():
    """DQ 규칙 현황 — 6 Dimensions 프레임워크 기반 규칙 목록 + 7일 발동 건수"""
    DQ_RULES = [
        {"dimension": "Completeness", "rule_name": "시간 슬롯 커버리지", "target": "shopping-events", "layer": "Stream", "anomaly_types": ["category_drop"]},
        {"dimension": "Validity", "rule_name": "이상가격 격리", "target": "shopping-events", "layer": "Stream", "anomaly_types": ["abnormal_price_spike"]},
        {"dimension": "Validity", "rule_name": "카테고리 누락 탐지", "target": "shopping-events", "layer": "Stream", "anomaly_types": ["category_drop"]},
        {"dimension": "Timeliness", "rule_name": "이벤트 지연 감시", "target": "shopping-events", "layer": "Stream", "anomaly_types": ["payment_drop"]},
        {"dimension": "Consistency", "rule_name": "교차 검증", "target": "dq_*_hourly", "layer": "ETL", "anomaly_types": ["reconciliation_mismatch"]},
    ]
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT anomaly_type, COUNT(*) as cnt
            FROM dq_anomaly_log
            WHERE detected_at >= NOW() - INTERVAL '7 days'
            GROUP BY anomaly_type
        """)
        counts = {r[0]: r[1] for r in cur.fetchall()}
        cur.close()
        conn.close()

        result = []
        for rule in DQ_RULES:
            trigger_count = sum(counts.get(at, 0) for at in rule["anomaly_types"])
            result.append({
                "dimension": rule["dimension"],
                "rule_name": rule["rule_name"],
                "target": rule["target"],
                "layer": rule["layer"],
                "trigger_count_7d": trigger_count,
                "status": "active"
            })
        return result
    except Exception as e:
        logger.error(f"dq/rules-summary failed: {e}")
        return []

@router.get("/dq/anomaly-raw-count")
async def get_dq_anomaly_raw_count():
    """이상 가격 격리 건수 (최근 24시간)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                anomaly_reason,
                COUNT(*) as count
            FROM dq_anomaly_raw
            WHERE detected_at >= NOW() - INTERVAL '24 hours'
            GROUP BY anomaly_reason
        """)
        rows = cur.fetchall()
        total = sum(r[1] for r in rows)
        breakdown = {r[0]: int(r[1]) for r in rows}
        cur.close()
        conn.close()
        return {"total": total, "breakdown": breakdown}
    except Exception as e:
        logger.error(f"dq/anomaly-raw-count failed: {e}")
        return {"total": 0, "breakdown": {}}

@router.get("/reports/latest")
def get_latest_report(date: str = None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        if date:
            cur.execute("""
                SELECT content, created_at
                FROM report_archive
                WHERE report_date = %s
                LIMIT 1
            """, (date,))
        else:
            cur.execute("""
                SELECT content, created_at
                FROM report_archive
                ORDER BY created_at DESC 
                LIMIT 1
            """)
            
        row = cur.fetchone()
        if not row:
            if date:
                return {"content": None, "created_at": None, "error": f"No report found for date {date}"}
            return {"content": None, "created_at": None, "error": "No reports found."}
        
        return {
            "content": row[0], 
            "created_at": row[1]
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

@router.get("/mart/rfm-distribution")
async def get_rfm_distribution():
    """RFM 세그먼트별 사용자 분포"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT rfm_segment as segment, COUNT(*) as user_count
            FROM mart_user_rfm
            GROUP BY segment
            ORDER BY user_count DESC
        """)
        rows = cur.fetchall()
        for r in rows:
            r['user_count'] = int(r['user_count'])
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"mart/rfm-distribution failed: {e}")
        return []


@router.get("/mart/product-association")
async def get_product_association(limit: int = 10):
    """상품 연관 규칙 (lift 기준 상위 N개)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT antecedents, consequents, confidence, lift, support
            FROM mart_product_association
            ORDER BY lift DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
        for r in rows:
            r['confidence'] = float(r['confidence'])
            r['lift'] = float(r['lift'])
            r['support'] = float(r['support'])
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"mart/product-association failed: {e}")
        return []


@router.get("/mart/daily-sales")
async def get_daily_sales(days: int = 7):
    """일별 매출 집계 (mart 테이블)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT date, category, total_revenue as revenue,
                   order_count as orders, avg_order_value as avg_value
            FROM mart_daily_sales
            WHERE date >= CURRENT_DATE - make_interval(days => %s)
            ORDER BY date DESC, revenue DESC
        """, (days,))
        rows = cur.fetchall()
        for r in rows:
            r['date'] = r['date'].isoformat() if hasattr(r['date'], 'isoformat') else str(r['date'])
            r['revenue'] = round(float(r['revenue']), 2)
            r['orders'] = int(r['orders'])
            r['avg_value'] = round(float(r['avg_value']), 2)
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"mart/daily-sales failed: {e}")
        return []


@router.get("/mart/weekly-trend")
async def get_weekly_trend(weeks: int = 8):
    """주별 매출 트렌드 (mart 테이블)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT week_start as week,
                   SUM(total_revenue) as revenue, SUM(order_count) as orders
            FROM mart_weekly_sales
            WHERE week_start >= CURRENT_DATE - make_interval(weeks => %s)
            GROUP BY week_start
            ORDER BY week DESC
        """, (weeks,))
        rows = cur.fetchall()
        for r in rows:
            r['week'] = r['week'].isoformat() if hasattr(r['week'], 'isoformat') else str(r['week'])
            r['revenue'] = round(float(r['revenue']), 2)
            r['orders'] = int(r['orders'])
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"mart/weekly-trend failed: {e}")
        return []


@router.get("/mart/daily-trend")
async def get_daily_trend():
    """7일 일별 요약 + DoD% — KPI 스파크라인 용도"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT date, total_revenue, total_orders, avg_order_value,
                ROUND(((total_revenue - LAG(total_revenue) OVER (ORDER BY date))
                    / NULLIF(LAG(total_revenue) OVER (ORDER BY date), 0) * 100)::numeric, 1) as dod_pct
            FROM mart_daily_summary
            ORDER BY date DESC LIMIT 8
        """)
        rows = cur.fetchall()
        for r in rows:
            r['date'] = r['date'].isoformat()
            r['total_revenue'] = float(r['total_revenue'] or 0)
            r['total_orders'] = int(r['total_orders'] or 0)
            r['avg_order_value'] = round(float(r['avg_order_value'] or 0), 1)
            r['dod_pct'] = float(r['dod_pct']) if r['dod_pct'] is not None else None
        cur.close()
        conn.close()
        return list(reversed(rows))
    except Exception as e:
        logger.error(f"mart/daily-trend failed: {e}")
        return []


@router.get("/mart/weekly-summary")
async def get_weekly_summary():
    """이번주 vs 지난주 요약 + WoW%"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            WITH weekly AS (
                SELECT week_start, SUM(total_revenue) as revenue, SUM(order_count) as orders
                FROM mart_weekly_sales GROUP BY week_start ORDER BY week_start DESC LIMIT 2
            )
            SELECT week_start, revenue, orders,
                LAG(revenue) OVER (ORDER BY week_start) as prev_revenue,
                LAG(orders) OVER (ORDER BY week_start) as prev_orders
            FROM weekly ORDER BY week_start DESC LIMIT 1
        """)
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return {}
        rev, orders = float(row[1]), int(row[2])
        prev_rev = float(row[3]) if row[3] else None
        prev_ord = int(row[4]) if row[4] else None

        # 이번주 베스트 카테고리
        cur.execute("""
            SELECT category, total_revenue FROM mart_weekly_sales
            WHERE week_start = (SELECT MAX(week_start) FROM mart_weekly_sales)
            ORDER BY total_revenue DESC LIMIT 1
        """)
        best = cur.fetchone()
        cur.close()
        conn.close()

        return {
            "week_start": row[0].isoformat(),
            "revenue": rev, "orders": orders,
            "wow_revenue_pct": round((rev - prev_rev) / prev_rev * 100, 1) if prev_rev and prev_rev > 0 else None,
            "wow_orders_pct": round((orders - prev_ord) / prev_ord * 100, 1) if prev_ord and prev_ord > 0 else None,
            "best_category": best[0] if best else None,
            "best_category_revenue": float(best[1]) if best else None,
            "total_week_revenue": rev,
        }
    except Exception as e:
        logger.error(f"mart/weekly-summary failed: {e}")
        return {}


@router.get("/mart/funnel-trend")
async def get_funnel_trend():
    """일별 퍼널 전환율 (shop_funnel_stats_log 집계)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT
                DATE(window_start + INTERVAL '9 hours') as date,
                SUM(total_sessions) as sessions,
                SUM(view_count) as views,
                SUM(cart_count) as carts,
                SUM(purchase_count) as purchases,
                ROUND((SUM(cart_count)::numeric / NULLIF(SUM(view_count),0) * 100)::numeric, 1) as cart_rate,
                ROUND((SUM(purchase_count)::numeric / NULLIF(SUM(cart_count),0) * 100)::numeric, 1) as purchase_rate,
                ROUND((SUM(purchase_count)::numeric / NULLIF(SUM(total_sessions),0) * 100)::numeric, 1) as overall_cvr
            FROM shop_funnel_stats_log
            WHERE window_start >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(window_start + INTERVAL '9 hours')
            ORDER BY date
        """)
        rows = cur.fetchall()
        for r in rows:
            r['date'] = r['date'].isoformat()
            for k in ['sessions','views','carts','purchases']:
                r[k] = int(r[k] or 0)
            for k in ['cart_rate','purchase_rate','overall_cvr']:
                r[k] = float(r[k]) if r[k] is not None else 0
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"mart/funnel-trend failed: {e}")
        return []


@router.get("/mart/category-ranking")
async def get_category_ranking():
    """카테고리 매출 랭킹 + WoW% 비교"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            WITH latest_week AS (SELECT MAX(week_start) as ws FROM mart_weekly_sales),
            this_week AS (
                SELECT category, total_revenue, order_count
                FROM mart_weekly_sales WHERE week_start = (SELECT ws FROM latest_week)
            ),
            last_week AS (
                SELECT category, total_revenue, order_count
                FROM mart_weekly_sales WHERE week_start = (SELECT ws FROM latest_week) - INTERVAL '7 days'
            )
            SELECT t.category, t.total_revenue as revenue, t.order_count as orders,
                ROUND(((t.total_revenue - COALESCE(l.total_revenue,0))
                    / NULLIF(l.total_revenue,0) * 100)::numeric, 1) as wow_pct
            FROM this_week t LEFT JOIN last_week l ON t.category = l.category
            ORDER BY t.total_revenue DESC
        """)
        rows = cur.fetchall()
        total = sum(float(r['revenue'] or 0) for r in rows)
        for r in rows:
            r['revenue'] = float(r['revenue'] or 0)
            r['orders'] = int(r['orders'] or 0)
            r['wow_pct'] = float(r['wow_pct']) if r['wow_pct'] is not None else None
            r['share_pct'] = round(r['revenue'] / total * 100, 1) if total > 0 else 0
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"mart/category-ranking failed: {e}")
        return []


@router.get("/dq/overview")
async def get_dq_overview():
    """DQ 통합 요약 — 스코어 + 어제 비교 + anomaly 카운트"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 최근 2일 DQ 스코어
        cur.execute("SELECT date,total_score,completeness_score,validity_score,timeliness_score FROM dq_daily_score ORDER BY date DESC LIMIT 2")
        scores = cur.fetchall()
        today_score = None
        yesterday_score = None
        score_detail = {}
        if scores:
            today_score = int(scores[0][1])
            score_detail = {"completeness": int(scores[0][2]), "validity": int(scores[0][3]), "timeliness": int(scores[0][4])}
        if len(scores) >= 2:
            yesterday_score = int(scores[1][1])

        # severity별 24h anomaly 카운트
        cur.execute("SELECT severity, COUNT(*) FROM dq_anomaly_log WHERE detected_at >= NOW() - INTERVAL '24 hours' GROUP BY severity")
        sev = {r[0]: int(r[1]) for r in cur.fetchall()}

        # 미해결 anomaly 수
        cur.execute("SELECT COUNT(*) FROM dq_anomaly_log WHERE resolved = FALSE")
        unresolved = int(cur.fetchone()[0])

        # 최대 reconciliation diff
        cur.execute("""
            WITH diffs AS (
                SELECT hour, ABS(c.total - p.total)::float / GREATEST(c.total, p.total, 1) * 100 as diff_pct
                FROM (SELECT hour, SUM(purchase_count) as total FROM dq_category_hourly WHERE hour >= NOW()-INTERVAL '24 hours' GROUP BY hour) c
                JOIN (SELECT hour, SUM(purchase_count) as total FROM dq_payment_hourly WHERE hour >= NOW()-INTERVAL '24 hours' GROUP BY hour) p USING(hour)
            ) SELECT ROUND(MAX(diff_pct)::numeric, 1) FROM diffs
        """)
        max_diff_row = cur.fetchone()
        max_diff = float(max_diff_row[0]) if max_diff_row and max_diff_row[0] else 0

        cur.close()
        conn.close()
        return {
            "score": today_score, "prev_score": yesterday_score,
            "score_change": today_score - yesterday_score if today_score and yesterday_score else None,
            "detail": score_detail,
            "anomalies_24h": sev, "unresolved": unresolved,
            "max_diff_pct": max_diff,
        }
    except Exception as e:
        logger.error(f"dq/overview failed: {e}")
        return {"score": None, "prev_score": None, "score_change": None, "detail": {}, "anomalies_24h": {}, "unresolved": 0, "max_diff_pct": 0}


@admin_router.post("/login")
def admin_login(req: LoginRequest):
    if req.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    
    token = jwt.encode({
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(hours=12)
    }, JWT_SECRET, algorithm="HS256")
    
    return {"token": token}

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
security = HTTPBearer()

def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return verify_token(credentials.credentials)

@admin_router.get("/settings")
def get_settings(admin=Depends(get_current_admin)):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, mode, base_tps, chaos_mode, category_bias, user_persona_bias, expires_at 
                FROM shop_generator_settings 
                ORDER BY id DESC LIMIT 1
            """)
            row = cur.fetchone()
            if row and row['expires_at']:
                row['expires_at'] = row['expires_at'].isoformat()
            return row or {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@admin_router.put("/settings")
def update_settings(settings: GeneratorSettingsUpdate, admin=Depends(get_current_admin)):
    conn = get_db_connection()
    try:
        expires_at = None
        if settings.duration_minutes:
            expires_at = datetime.now() + timedelta(minutes=settings.duration_minutes)

        with conn.cursor() as cur:
            cur.execute("""
                UPDATE shop_generator_settings 
                SET mode = %s, base_tps = %s, chaos_mode = %s, category_bias = %s, 
                    user_persona_bias = %s, expires_at = %s, updated_at = NOW()
                WHERE id = 1
            """, (settings.mode, settings.base_tps, settings.chaos_mode, 
                  settings.category_bias, settings.user_persona_bias, expires_at))
            conn.commit()

        # Publish to Kafka
        if producer:
            payload = {
                "type": "UPDATE_SETTINGS",
                "settings": {
                    "mode": settings.mode,
                    "base_tps": settings.base_tps,
                    "chaos_mode": settings.chaos_mode,
                    "category_bias": settings.category_bias,
                    "user_persona_bias": settings.user_persona_bias,
                    "expires_at": expires_at.isoformat() if expires_at else None
                }
            }
            producer.send("generator-control", value=payload)
            producer.flush()

        return {"status": "success", "expires_at": expires_at}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

app.include_router(router)
app.include_router(admin_router)
