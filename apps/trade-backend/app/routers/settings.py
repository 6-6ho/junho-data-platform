from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import List

from ..database import get_db
from ..models.base import FavoriteGroup, FavoriteItem
from ..auth import get_current_user

router = APIRouter(prefix="/api/settings", tags=["settings"])

WATCHLIST_GROUP_NAME = "Watchlist"


class WatchlistAddRequest(BaseModel):
    symbol: str


def _get_or_create_watchlist_group(db: Session) -> FavoriteGroup:
    group = db.query(FavoriteGroup).filter(FavoriteGroup.name == WATCHLIST_GROUP_NAME).first()
    if not group:
        group = FavoriteGroup(name=WATCHLIST_GROUP_NAME, ordering=0)
        db.add(group)
        db.commit()
        db.refresh(group)
    return group


@router.get("/watchlist", response_model=List[str])
def get_watchlist(db: Session = Depends(get_db), _user: str = Depends(get_current_user)):
    group = _get_or_create_watchlist_group(db)
    items = db.query(FavoriteItem.symbol).filter(FavoriteItem.group_id == group.group_id).order_by(FavoriteItem.ordering).all()
    return [item.symbol for item in items]


@router.post("/watchlist")
def add_watchlist_symbol(req: WatchlistAddRequest, db: Session = Depends(get_db), _user: str = Depends(get_current_user)):
    symbol = req.symbol.upper()

    # Validate symbol exists in market_snapshot
    result = db.execute(text("SELECT 1 FROM market_snapshot WHERE symbol = :s LIMIT 1"), {"s": symbol}).fetchone()
    if not result:
        raise HTTPException(status_code=400, detail=f"Unknown symbol: {symbol}")

    group = _get_or_create_watchlist_group(db)

    # Check duplicate
    exists = db.query(FavoriteItem).filter(
        FavoriteItem.group_id == group.group_id,
        FavoriteItem.symbol == symbol
    ).first()
    if exists:
        raise HTTPException(status_code=409, detail=f"{symbol} already in watchlist")

    item = FavoriteItem(group_id=group.group_id, symbol=symbol)
    db.add(item)
    db.commit()
    return {"status": "added", "symbol": symbol}


@router.delete("/watchlist/{symbol}")
def remove_watchlist_symbol(symbol: str, db: Session = Depends(get_db), _user: str = Depends(get_current_user)):
    symbol = symbol.upper()
    group = _get_or_create_watchlist_group(db)
    item = db.query(FavoriteItem).filter(
        FavoriteItem.group_id == group.group_id,
        FavoriteItem.symbol == symbol
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"{symbol} not in watchlist")
    db.delete(item)
    db.commit()
    return {"status": "removed", "symbol": symbol}
