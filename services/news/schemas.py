from datetime import datetime
from pydantic import BaseModel, ConfigDict


class NewsItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class NewsQuery(BaseModel):
    q: str | None = None
    market: str | None = None
    source: str | None = None
    limit: int = 50


class MarketIndexOut(BaseModel):
    name: str
    value: str
    change: float
    amount: str
    news_id: int | None = None
    news_title: str | None = None


class MarketSentimentOut(BaseModel):
    score: int
    label: str
    weather: str


class MarketDistributionOut(BaseModel):
    up: int
    flat: int
    down: int
    label: str


class MarketTurnoverOut(BaseModel):
    current: str
    compare: float
    label: str


class MarketBentoOut(BaseModel):
    indices: list[MarketIndexOut]
    sentiment: MarketSentimentOut
    distribution: MarketDistributionOut
    turnover: MarketTurnoverOut
