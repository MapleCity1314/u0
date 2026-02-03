from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from services.core.base import Base


class LogEntry(Base):
    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(16), nullable=False)
    module = Column(String(64), nullable=True)
    request_id = Column(String(64), nullable=True)
    message = Column(Text, nullable=False)
    error = Column(Text, nullable=True)
    extra = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
