"""
Shop Analytics API Router
EDA 대시보드용 API 엔드포인트
"""
from fastapi import APIRouter
import psycopg2
import os

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("POSTGRES_DB", "app"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres")
    )

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

@router.get("/hourly-traffic")
async def get_hourly_traffic():
    """시간대별 트래픽"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                EXTRACT(HOUR FROM window_start) as hour,
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
