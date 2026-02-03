import asyncio
import json
from fastapi import APIRouter
from starlette.responses import StreamingResponse

from services.core.database import SessionLocal
from services.news.models.news import NewsItem

router = APIRouter()


def _format_event(item: NewsItem) -> str:
    payload = {
        "id": item.id,
        "source": item.source,
        "market": item.market,
        "title": item.title,
        "url": item.url,
        "summary": item.summary,
        "tags": item.tags,
        "published_at": item.published_at.isoformat() if item.published_at else None,
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.get("/news/stream")
async def stream_news():
    async def event_generator():
        last_id = 0
        while True:
            db = SessionLocal()
            try:
                latest = (
                    db.query(NewsItem)
                    .filter(NewsItem.id > last_id)
                    .order_by(NewsItem.id.asc())
                    .limit(50)
                    .all()
                )
                for item in latest:
                    last_id = item.id
                    yield _format_event(item)
            finally:
                db.close()
            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
