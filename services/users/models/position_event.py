from sqlalchemy import Column, DateTime, Float, Integer, String, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from services.core.base import Base


class PositionEvent(Base):
    __tablename__ = "position_events"

    id = Column(Integer, primary_key=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_type = Column(String(16), nullable=False)
    delta_units = Column(Float, nullable=True)
    delta_amount = Column(Float, nullable=True)
    delta_cost = Column(Float, nullable=True)
    payload = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


Index("ix_position_events_user", PositionEvent.user_id)
Index("ix_position_events_position", PositionEvent.position_id)
Index("ix_position_events_type", PositionEvent.event_type)
