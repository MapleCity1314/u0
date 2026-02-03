from datetime import datetime
from pydantic import BaseModel


class NewsItemOut(BaseModel):
    id: int
    source: str
    market: str | None = None
    title: str
    url: str | None = None
    summary: str | None = None
    tags: str | None = None
    fingerprint: str | None = None
    published_at: datetime | None = None
    created_at: datetime | None = None

    class Config:
        orm_mode = True


class NewsQuery(BaseModel):
    q: str | None = None
    market: str | None = None
    source: str | None = None
    limit: int = 50
