from sqlalchemy import Column, DateTime, Float, Integer, String, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from services.core.base import Base


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    code = Column(String(16), nullable=False)
    units = Column(Float, nullable=True)
    cost = Column(Float, nullable=True)
    amount = Column(Float, nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    source = Column(String(16), nullable=False, default="manual")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


Index("ix_positions_user", Position.user_id)
Index("ix_positions_code", Position.code)
Index("ix_positions_active", Position.is_active)
Index("uq_positions_user_code_active", Position.user_id, Position.code, Position.is_active, unique=True)
