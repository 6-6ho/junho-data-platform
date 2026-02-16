from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = FastAPI(title="Shop Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use /api prefix to match existing frontend proxy
router = APIRouter(prefix="/api/analytics", tags=["analytics"])

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("POSTGRES_DB", "app"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres")
    )

@app.get("/")
def read_root():
    return {"status": "ok", "service": "shop-backend"}

@router.get("/summary")
async def get_summary():
    """전체 요약 통계"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Total orders (order_count 합계)
        cur.execute("SELECT COALESCE(SUM(order_count), 0) FROM shop_brand_stats_log")
        total_events = cur.fetchone()[0] or 0
        
        # Today's records
        cur.execute("""
            SELECT COUNT(*) FROM shop_brand_stats_log 
            WHERE window_start >= NOW() - INTERVAL '24 hours'
        """)
        today_records = cur.fetchone()[0] or 0
        
        # Conversion rate from funnel
        cur.execute("""
            SELECT 
                COALESCE(SUM(view_count), 1) as views,
                COALESCE(SUM(purchase_count), 0) as purchases
            FROM shop_funnel_stats_log
            WHERE window_start >= NOW() - INTERVAL '24 hours'
        """)
        row = cur.fetchone()
        views = row[0] or 1
        purchases = row[1] or 0
        conversion_rate = (purchases / views * 100) if views > 0 else 0
        
        # Top brands by total_revenue
        cur.execute("""
            SELECT brand_name FROM shop_brand_stats_log
            GROUP BY brand_name
            ORDER BY SUM(total_revenue) DESC
            LIMIT 5
        """)
        top_brands = [r[0] for r in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return {
            "total_events": int(total_events),
            "today_records": int(today_records),
            "conversion_rate": round(conversion_rate, 2),
            "top_brands": top_brands
        }
    except Exception as e:
        return {
            "total_events": 0,
            "today_records": 0,
            "conversion_rate": 0,
            "top_brands": [],
            "error": str(e)
        }

@router.get("/affinity")
def get_affinity_rules(limit: int = 10, min_confidence: float = 0.1):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get top rules by confidence
            cur.execute("""
                SELECT 
                    antecedents,
                    consequents,
                    confidence,
                    lift,
                    support
                FROM mart_product_association
                WHERE confidence >= %s
                ORDER BY confidence DESC
                LIMIT %s
            """, (min_confidence, limit))
            rules = cur.fetchall()
            return {
                "rules": rules,
                "count": len(rules)
            }
    except Exception as e:
        print(f"Error fetching affinity rules: {e}")
        return {"rules": [], "count": 0}
    finally:
        conn.close()

@router.get("/rfm")
def get_rfm_segments():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    rfm_segment, 
                    count(*) as count 
                FROM mart_user_rfm 
                GROUP BY rfm_segment 
                ORDER BY count DESC
            """)
            rows = cur.fetchall()
            
            total = sum(r[1] for r in rows) or 1
            
            result = [
                {
                    "segment": r[0],
                    "count": r[1],
                    "percentage": round(r[1] / total * 100, 1)
                }
                for r in rows
            ]
            
            return result
    except Exception as e:
        print(f"Error fetching RFM: {e}")
        return []
    finally:
        conn.close()

@router.get("/hourly-traffic")
async def get_hourly_traffic():
    """시간대별 트래픽"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                EXTRACT(HOUR FROM window_start AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul') as hour,
                COALESCE(SUM(order_count), 0) as count
            FROM shop_brand_stats_log
            WHERE window_start >= NOW() - INTERVAL '24 hours'
            GROUP BY 1
            ORDER BY 1
        """)
        
        result = [{"hour": int(r[0]), "count": int(r[1])} for r in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return result
    except Exception as e:
        return []

@router.get("/brand-distribution")
async def get_brand_distribution():
    """브랜드별 주문 분포"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                brand_name,
                COALESCE(SUM(order_count), 0) as count
            FROM shop_brand_stats_log
            GROUP BY brand_name
            ORDER BY count DESC
            LIMIT 20
        """)
        
        rows = cur.fetchall()
        total = sum(r[1] for r in rows) or 1
        
        result = [
            {
                "brand": r[0],
                "count": int(r[1]),
                "percentage": round(r[1] / total * 100, 1)
            }
            for r in rows
        ]
        
        cur.close()
        conn.close()
        
        return result
    except Exception as e:
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
        return {
            "page_view": 0,
            "add_to_cart": 0,
            "purchase": 0,
            "conversion_rate": 0
        }

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

app.include_router(router)
