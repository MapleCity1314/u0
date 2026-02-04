from datetime import datetime, timedelta, timezone
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from services.core.database import get_db
from services.logs.utils import log_event
from services.news.models.news import NewsItem
from services.news.market_data import fetch_market_indices
from services.news.schemas import MarketBentoOut, NewsItemOut

router = APIRouter()

MARKET_MAP = {
    "cn": "CN",
    "hk": "HK",
    "us": "US",
    "gl": "GL",
    "gold": "GL",
}

POSITIVE_KEYWORDS = [
    "上涨",
    "走强",
    "反弹",
    "创新高",
    "利好",
    "增持",
    "回升",
    "增长",
    "上调",
    "突破",
    "rally",
    "surge",
    "gain",
    "beats",
    "upgrade",
    "record high",
]

NEGATIVE_KEYWORDS = [
    "下跌",
    "回落",
    "走弱",
    "暴跌",
    "利空",
    "减持",
    "下调",
    "亏损",
    "风险",
    "下行",
    "疲弱",
    "selloff",
    "drop",
    "slump",
    "misses",
    "downgrade",
    "record low",
]


def _classify_sentiment(text: str) -> str:
    if not text:
        return "flat"
    lower = text.lower()
    pos = sum(1 for kw in POSITIVE_KEYWORDS if kw in lower)
    neg = sum(1 for kw in NEGATIVE_KEYWORDS if kw in lower)
    if pos > neg:
        return "up"
    if neg > pos:
        return "down"
    return "flat"


def _sentiment_summary(up: int, down: int, total: int) -> tuple[int, str, str]:
    if total <= 0:
        return 50, "中性", "cloudy"
    score = int(max(0, min(100, 50 + ((up - down) / max(total, 1)) * 50)))
    if score >= 70:
        return score, "偏多情绪", "sunny"
    if score <= 40:
        return score, "偏空情绪", "rainy"
    return score, "中性偏稳", "cloudy"


def _query_source_counts(db: Session, market: str, start: datetime, end: datetime) -> dict[str, int]:
    ts = func.coalesce(NewsItem.published_at, NewsItem.created_at)
    rows = (
        db.query(NewsItem.source, func.count(NewsItem.id))
        .filter(NewsItem.market == market)
        .filter(ts >= start, ts < end)
        .group_by(NewsItem.source)
        .all()
    )
    return {source: int(count) for source, count in rows}


def _build_market_bento(db: Session, market: str) -> MarketBentoOut:
    now = datetime.now(timezone.utc)
    window = timedelta(hours=24)
    start_recent = now - window
    start_prev = now - window * 2

    ts = func.coalesce(NewsItem.published_at, NewsItem.created_at)
    recent_items = (
        db.query(NewsItem.title, NewsItem.summary)
        .filter(NewsItem.market == market)
        .filter(ts >= start_recent)
        .order_by(ts.desc())
        .limit(500)
        .all()
    )

    up = down = flat = 0
    for title, summary in recent_items:
        sentiment = _classify_sentiment(f"{title or ''} {summary or ''}")
        if sentiment == "up":
            up += 1
        elif sentiment == "down":
            down += 1
        else:
            flat += 1

    total = up + down + flat
    score, label, weather = _sentiment_summary(up, down, total)

    recent_counts = _query_source_counts(db, market, start_recent, now)
    prev_counts = _query_source_counts(db, market, start_prev, start_recent)

    try:
        quotes = fetch_market_indices(market)
    except Exception as exc:
        log_event("error", "news.api", "market_quote_failed", error=str(exc))
        quotes = []

    news_items = (
        db.query(NewsItem.id, NewsItem.title)
        .filter(NewsItem.market == market)
        .order_by(ts.desc(), NewsItem.id.desc())
        .limit(20)
        .all()
    )

    indices = []
    for idx, quote in enumerate(quotes[:4]):
        news = news_items[idx] if idx < len(news_items) else None
        indices.append(
            {
                "name": quote.name,
                "value": quote.value,
                "change": round(quote.change, 2),
                "amount": quote.amount,
                "news_id": news.id if news else None,
                "news_title": news.title if news else None,
            }
        )

    while len(indices) < 4:
        indices.append(
            {
                "name": "暂无指数",
                "value": "0",
                "change": 0.0,
                "amount": "-",
                "news_id": None,
                "news_title": None,
            }
        )

    prev_total = sum(prev_counts.values())
    current_total = sum(recent_counts.values())
    compare = 0.0
    if prev_total > 0:
        compare = ((current_total - prev_total) / prev_total) * 100
    elif current_total > 0:
        compare = 100.0

    return MarketBentoOut(
        indices=indices,
        sentiment={"score": score, "label": label, "weather": weather},
        distribution={"up": up, "flat": flat, "down": down, "label": "条"},
        turnover={
            "current": f"{current_total}条",
            "compare": round(compare, 2),
            "label": "近24小时新闻",
        },
    )


@router.get("/news", response_model=list[NewsItemOut])
def list_news(
    q: str | None = None,
    market: str | None = None,
    source: str | None = None,
    cursor: int | None = None,
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
        if cursor:
            query = query.filter(NewsItem.id < cursor)
        return query.order_by(NewsItem.published_at.desc(), NewsItem.id.desc()).limit(limit).all()
    except Exception as exc:
        log_event("error", "news.api", "query_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="news_query_failed")


@router.get("/news/market-bento", response_model=MarketBentoOut)
def market_bento(
    market: str = Query(..., description="cn/hk/us/gl"),
    db: Session = Depends(get_db),
):
    try:
        normalized = MARKET_MAP.get(market.lower(), market.upper())
        return _build_market_bento(db, normalized)
    except Exception as exc:
        log_event("error", "news.api", "market_bento_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="news_market_bento_failed")


@router.get("/news/{news_id}", response_model=NewsItemOut)
def get_news(
    news_id: int,
    db: Session = Depends(get_db),
):
    item = db.query(NewsItem).filter(NewsItem.id == news_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="news_not_found")
    return item
