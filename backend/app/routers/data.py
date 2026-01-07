from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..database import get_db
from ..models.base import MoverLatest, AlertEvent

from typing import List
from ..schemas import MoverResponse, AlertResponse

router = APIRouter(prefix="/api", tags=["data"])

@router.get("/movers/latest", response_model=List[MoverResponse])
def get_movers(limit: int = 20, db: Session = Depends(get_db)):
    # Deduplicate: Get only the latest event per symbol
    # Using a subquery to find max event_time per symbol, then join
    from sqlalchemy import func
    
    subquery = db.query(
        MoverLatest.symbol,
        MoverLatest.type,
        func.max(MoverLatest.event_time).label("max_event_time")
    ).group_by(MoverLatest.symbol, MoverLatest.type).subquery()
    
    query = db.query(MoverLatest).join(
        subquery,
        (MoverLatest.symbol == subquery.c.symbol) & 
        (MoverLatest.type == subquery.c.type) &
        (MoverLatest.event_time == subquery.c.max_event_time)
    ).order_by(desc(MoverLatest.event_time)).limit(limit)
    
    return query.all()

@router.get("/alerts/latest", response_model=List[AlertResponse])
def get_alerts(symbol: str = None, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(AlertEvent)
    if symbol:
        query = query.filter(AlertEvent.symbol == symbol)
    return query.order_by(desc(AlertEvent.event_time)).limit(limit).all()
