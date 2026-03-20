"""
Listing Router — 신규 상장 이벤트 API
- GET /api/listing/recent  → 최근 상장 목록
- GET /api/listing/stats   → 기간별 상장 통계
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/api/listing", tags=["listing"])


@router.get("/recent")
def listing_recent(
    limit: int = Query(20, ge=1, le=100),
    exchange: Optional[str] = Query(None, description="upbit | bithumb"),
    db: Session = Depends(get_db),
):
    """최근 신규 상장 목록."""
    conditions = []
    params = {"limit": limit}

    if exchange:
        conditions.append("exchange = :exchange")
        params["exchange"] = exchange

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    rows = db.execute(text(f"""
        SELECT id, exchange, symbol, market_code, korean_name, english_name, detected_at
        FROM listing_event
        WHERE {where_clause}
        ORDER BY detected_at DESC
        LIMIT :limit
    """), params).fetchall()

    events = []
    for r in rows:
        events.append({
            "id": r[0],
            "exchange": r[1],
            "symbol": r[2],
            "market_code": r[3],
            "korean_name": r[4],
            "english_name": r[5],
            "detected_at": r[6].isoformat() if r[6] else None,
        })

    return {"events": events, "count": len(events)}


@router.get("/stats")
def listing_stats(db: Session = Depends(get_db)):
    """기간별 신규 상장 통계."""
    row = db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE detected_at > NOW() - INTERVAL '24 hours') AS last_24h,
            COUNT(*) FILTER (WHERE detected_at > NOW() - INTERVAL '7 days') AS last_7d,
            COUNT(*) FILTER (WHERE detected_at > NOW() - INTERVAL '30 days') AS last_30d
        FROM listing_event
    """)).fetchone()

    return {
        "last_24h": row[0] if row else 0,
        "last_7d": row[1] if row else 0,
        "last_30d": row[2] if row else 0,
    }
