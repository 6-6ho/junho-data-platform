from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID

class MoverResponse(BaseModel):
    type: str
    symbol: str
    status: str
    window: str
    event_time: datetime
    change_pct_window: float
    change_pct_24h: float
    vol_ratio: Optional[float] = None

    class Config:
        from_attributes = True

class AlertResponse(BaseModel):
    event_time: datetime
    symbol: str
    line_id: UUID
    direction: str
    price: float
    line_price: float
    buffer_pct: float

    class Config:
        from_attributes = True

from typing import List

class FavoriteItemBase(BaseModel):
    symbol: str

class FavoriteItemCreate(FavoriteItemBase):
    group_id: UUID

class FavoriteItemResponse(FavoriteItemBase):
    item_id: UUID
    group_id: UUID
    ordering: int
    created_at: datetime
    class Config:
        from_attributes = True

class FavoriteGroupBase(BaseModel):
    name: str

class FavoriteGroupCreate(FavoriteGroupBase):
    pass

class FavoriteGroupResponse(FavoriteGroupBase):
    group_id: UUID
    ordering: int
    created_at: datetime
    items: List[FavoriteItemResponse] = []
    class Config:
        from_attributes = True
