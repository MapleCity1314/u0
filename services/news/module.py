from fastapi import FastAPI

from services.logs.utils import log_event
from services.news.api.routes import router as news_router
from services.news.api.sse import router as sse_router
from services.news.tasks.collector import start_background_collector


def register(app: FastAPI) -> None:
    app.include_router(news_router, prefix="/api", tags=["news"])
    app.include_router(sse_router, prefix="/api", tags=["news"])
    try:
        start_background_collector()
    except Exception as exc:
        log_event("error", "news.module", "collector_start_failed", error=str(exc))
