from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from services.core.base import Base


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    code = Column(String(16), nullable=False)
    name = Column(String(128), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


Index("ix_watchlist_user", WatchlistItem.user_id)
Index("ix_watchlist_code", WatchlistItem.code)
Index("ix_watchlist_active", WatchlistItem.is_active)
Index(
    "uq_watchlist_user_code_active",
    WatchlistItem.user_id,
    WatchlistItem.code,
    WatchlistItem.is_active,
    unique=True,
)
