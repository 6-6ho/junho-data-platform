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
    """파이프라인 개요: 총 처리 이벤트, 오늘 처리량, 오늘 매출, 데이터 신선도"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 단일 쿼리로 24h 데이터만 집계 (인덱스 활용)
        cur.execute("""
            SELECT
                COALESCE(SUM(event_count), 0) as today_events,
                COALESCE(SUM(total_revenue), 0) as today_revenue
            FROM dq_category_hourly
            WHERE hour >= NOW() - INTERVAL '24 hours'
        """)
        row = cur.fetchone()
        today_events = row[0] or 0
        today_revenue = float(row[1] or 0)

        # Total events는 approximate (pg_stat 활용)
        cur.execute("""
            SELECT reltuples::bigint FROM pg_class WHERE relname = 'dq_category_hourly'
        """)
        total_events = cur.fetchone()[0] or 0

        # Data freshness (최근 created_at만 — 인덱스 활용)
        cur.execute("""
            SELECT EXTRACT(EPOCH FROM (NOW() - created_at))
            FROM shop_hourly_sales_log ORDER BY created_at DESC LIMIT 1
        """)
        freshness_row = cur.fetchone()
        data_freshness_sec = int(freshness_row[0]) if freshness_row and freshness_row[0] else None

        cur.close()
        conn.close()

        return {
            "total_events": int(total_events),
            "today_events": int(today_events),
            "today_revenue": round(today_revenue, 0),
            "data_freshness_sec": data_freshness_sec
        }
    except Exception as e:
        logger.error(f"summary failed: {e}")
        return {
            "total_events": 0,
            "today_events": 0,
            "today_revenue": 0,
            "data_freshness_sec": None,
            "error": str(e)
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
