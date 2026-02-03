from sqlalchemy import Column, DateTime, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.sql import func

from services.core.base import Base


class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(128), nullable=False)
    market = Column(String(32), nullable=True)
    title = Column(String(512), nullable=False)
    url = Column(String(1024), nullable=True)
    summary = Column(Text, nullable=True)
    tags = Column(String(256), nullable=True)
    fingerprint = Column(String(64), nullable=False)
    search_vector = Column(TSVECTOR)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


Index("ix_news_items_published", NewsItem.published_at)
Index("ix_news_items_source", NewsItem.source)
Index("ix_news_items_market", NewsItem.market)
Index("ix_news_items_title", NewsItem.title)
Index("ix_news_items_fingerprint", NewsItem.fingerprint, unique=True)
Index("ix_news_items_search_vector", NewsItem.search_vector, postgresql_using="gin")
