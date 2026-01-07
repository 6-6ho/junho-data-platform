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
