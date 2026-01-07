from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db, engine, Base
from ..models.base import FavoriteGroup, FavoriteItem
from ..schemas import FavoriteGroupCreate, FavoriteGroupResponse, FavoriteItemCreate, FavoriteItemResponse
from typing import List
from uuid import UUID

router = APIRouter(prefix="/api/favorites", tags=["favorites"])

# Auto-migration on startup (ensures tables exist)
Base.metadata.create_all(bind=engine)

@router.get("", response_model=List[FavoriteGroupResponse])
def get_favorites(db: Session = Depends(get_db)):
    return db.query(FavoriteGroup).order_by(FavoriteGroup.ordering).all()

@router.post("/groups", response_model=FavoriteGroupResponse)
def create_group(group: FavoriteGroupCreate, db: Session = Depends(get_db)):
    db_group = FavoriteGroup(name=group.name)
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group

@router.delete("/groups/{group_id}")
def delete_group(group_id: UUID, db: Session = Depends(get_db)):
    db_group = db.query(FavoriteGroup).filter(FavoriteGroup.group_id == group_id).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="Group not found")
    db.delete(db_group)
    db.commit()
    return {"status": "success"}

@router.post("/items", response_model=FavoriteItemResponse)
def create_item(item: FavoriteItemCreate, db: Session = Depends(get_db)):
    # Check if group exists
    group = db.query(FavoriteGroup).filter(FavoriteGroup.group_id == item.group_id).first()
    if not group:
         raise HTTPException(status_code=404, detail="Group not found")
         
    db_item = FavoriteItem(group_id=item.group_id, symbol=item.symbol.upper())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/items/{item_id}")
def delete_item(item_id: UUID, db: Session = Depends(get_db)):
    db_item = db.query(FavoriteItem).filter(FavoriteItem.item_id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()
    return {"status": "success"}
