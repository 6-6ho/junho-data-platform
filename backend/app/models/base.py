from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, UUID
from sqlalchemy.sql import func
import uuid
from ..database import Base

class Trendline(Base):
    __tablename__ = "trendlines"

    line_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String, nullable=False, index=True)
    t1_ms = Column(Integer, nullable=False) # bigint in DB, but python int handles it
    p1 = Column(Float, nullable=False)
    t2_ms = Column(Integer, nullable=False)
    p2 = Column(Float, nullable=False)
    basis = Column(String, default="close")
    mode = Column(String, default="both")
    buffer_pct = Column(Float, default=0.1)
    cooldown_sec = Column(Integer, default=600)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class MoverLatest(Base):
    __tablename__ = "movers_latest"
    # Composite PK in DB: type, symbol, status, event_time
    # SQLAlchemy needs explicit PK mapping usually.
    # We'll map mostly for Read.
    type = Column(String, primary_key=True)
    symbol = Column(String, primary_key=True)
    status = Column(String, primary_key=True)
    window = Column(String)
    event_time = Column(DateTime(timezone=True), primary_key=True)
    change_pct_window = Column(Float)
    change_pct_24h = Column(Float)
    vol_ratio = Column(Float, nullable=True)
    updated_at = Column(DateTime(timezone=True))

class AlertEvent(Base):
    __tablename__ = "alerts_events"
    
    # DB has no unique PK defined in DDL aside from implicit rowid.
    # We might need a dummy PK for SQLAlchemy or map without it.
    # For now, let's assume we just read them.
    event_time = Column(DateTime(timezone=True), primary_key=True) # Fake PK for standard SQLA
    symbol = Column(String, primary_key=True)
    line_id = Column(UUID(as_uuid=True), primary_key=True)
    direction = Column(String)
    price = Column(Float)
    line_price = Column(Float)
    buffer_pct = Column(Float)
    created_at = Column(DateTime(timezone=True))
