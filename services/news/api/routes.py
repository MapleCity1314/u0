from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from services.core.database import get_db
from services.logs.utils import log_event
from services.news.models.news import NewsItem
from services.news.schemas import NewsItemOut

router = APIRouter()


@router.get("/news", response_model=list[NewsItemOut])
def list_news(
    q: str | None = None,
    market: str | None = None,
    source: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    try:
        query = db.query(NewsItem)
        if q:
            query = query.filter(
                NewsItem.search_vector.op("@@")(func.plainto_tsquery("simple", q))
            )
        if market:
            query = query.filter(NewsItem.market == market)
        if source:
            query = query.filter(NewsItem.source == source)
        return query.order_by(NewsItem.published_at.desc()).limit(limit).all()
    except Exception as exc:
        log_event("error", "news.api", "query_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="news_query_failed")
