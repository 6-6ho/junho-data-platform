"""
Screener Router — 잡코인 스크리너 API
- GET /api/screener/overview  → 요약 통계
- GET /api/screener/coins     → 종목 리스트 (필터/정렬)
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.get("/overview")
def screener_overview(db: Session = Depends(get_db)):
    """요약: 총 종목, 잡코인 수, 분류별 count"""
    row = db.execute(text("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE junk_score > 0) AS junk_count,
            COUNT(*) FILTER (WHERE is_low_cap) AS low_cap_count,
            COUNT(*) FILTER (WHERE is_long_decline) AS long_decline_count,
            COUNT(*) FILTER (WHERE is_no_pump) AS no_pump_count,
            MAX(updated_at) AS last_updated
        FROM coin_screener_latest
    """)).fetchone()

    if not row or row[0] == 0:
        return {
            "total": 0,
            "junk_count": 0,
            "low_cap_count": 0,
            "long_decline_count": 0,
            "no_pump_count": 0,
            "last_updated": None,
        }

    return {
        "total": row[0],
        "junk_count": row[1],
        "low_cap_count": row[2],
        "long_decline_count": row[3],
        "no_pump_count": row[4],
        "last_updated": row[5].isoformat() if row[5] else None,
    }


@router.get("/coins")
def screener_coins(
    exchange: Optional[str] = Query(None, description="upbit | bithumb"),
    flag: Optional[str] = Query(None, description="low_cap | long_decline | no_pump | junk"),
    sort: Optional[str] = Query("junk_score", description="junk_score | market_cap | volume"),
    db: Session = Depends(get_db),
):
    """종목 리스트 (필터/정렬)"""
    conditions = []
    params = {}

    # 거래소 필터
    if exchange:
        conditions.append("exchange = :exchange")
        params["exchange"] = exchange

    # 분류 필터
    if flag == "low_cap":
        conditions.append("is_low_cap = TRUE")
    elif flag == "long_decline":
        conditions.append("is_long_decline = TRUE")
    elif flag == "no_pump":
        conditions.append("is_no_pump = TRUE")
    elif flag == "junk":
        conditions.append("junk_score > 0")

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    # 정렬
    order_map = {
        "junk_score": "junk_score DESC, market_cap_krw ASC NULLS LAST",
        "market_cap": "market_cap_krw ASC NULLS LAST",
        "volume": "volume_24h_krw DESC NULLS LAST",
    }
    order_clause = order_map.get(sort or "junk_score", order_map["junk_score"])

    sql = f"""
        SELECT exchange, symbol, price_krw, market_cap_krw, volume_24h_krw,
               weekly_down_count, listing_age_days,
               max_price_since_listing, listing_price,
               is_low_cap, is_long_decline, is_no_pump, junk_score,
               updated_at
        FROM coin_screener_latest
        WHERE {where_clause}
        ORDER BY {order_clause}
    """

    rows = db.execute(text(sql), params).fetchall()

    coins = []
    for r in rows:
        coins.append({
            "exchange": r[0],
            "symbol": r[1],
            "price_krw": r[2],
            "market_cap_krw": r[3],
            "volume_24h_krw": r[4],
            "weekly_down_count": r[5],
            "listing_age_days": r[6],
            "max_price_since_listing": r[7],
            "listing_price": r[8],
            "is_low_cap": r[9],
            "is_long_decline": r[10],
            "is_no_pump": r[11],
            "junk_score": r[12],
            "updated_at": r[13].isoformat() if r[13] else None,
        })

    return {"coins": coins, "count": len(coins)}
