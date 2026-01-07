from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from pydantic import BaseModel
from typing import List, Optional

from ..database import get_db
from ..models.base import Trendline

router = APIRouter(prefix="/api/trendlines", tags=["trendlines"])

# Pydantic Schemas
class TrendlineBase(BaseModel):
    symbol: str
    t1_ms: int
    p1: float
    t2_ms: int
    p2: float
    basis: str = "close"
    mode: str = "both"
    buffer_pct: float = 0.1
    cooldown_sec: int = 600
    enabled: bool = True

class TrendlineCreate(TrendlineBase):
    pass

class TrendlineUpdate(BaseModel):
    p1: Optional[float] = None
    p2: Optional[float] = None
    t1_ms: Optional[int] = None
    t2_ms: Optional[int] = None
    enabled: Optional[bool] = None

class TrendlineOut(TrendlineBase):
    line_id: UUID
    
    class Config:
        from_attributes = True

@router.get("", response_model=List[TrendlineOut])
def get_trendlines(symbol: str, db: Session = Depends(get_db)):
    return db.query(Trendline).filter(Trendline.symbol == symbol).all()

@router.post("", response_model=TrendlineOut)
def create_trendline(line: TrendlineCreate, db: Session = Depends(get_db)):
    db_line = Trendline(**line.dict())
    db.add(db_line)
    db.commit()
    db.refresh(db_line)
    return db_line

@router.put("/{line_id}", response_model=TrendlineOut)
def update_trendline(line_id: UUID, line: TrendlineUpdate, db: Session = Depends(get_db)):
    db_line = db.query(Trendline).filter(Trendline.line_id == line_id).first()
    if not db_line:
        raise HTTPException(status_code=404, detail="Trendline not found")
    
    for k, v in line.dict(exclude_unset=True).items():
        setattr(db_line, k, v)
    
    db.commit()
    db.refresh(db_line)
    return db_line

@router.delete("/{line_id}")
def delete_trendline(line_id: UUID, db: Session = Depends(get_db)):
    db_line = db.query(Trendline).filter(Trendline.line_id == line_id).first()
    if not db_line:
        raise HTTPException(status_code=404, detail="Trendline not found")
    
    db.delete(db_line)
    db.commit()
    return {"status": "deleted"}
