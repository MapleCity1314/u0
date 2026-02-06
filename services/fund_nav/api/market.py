import os
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query

from services.modules.redis_cache import get_cache
from ..data import akshare_client as data
from ..models.schemas import ApiResponse

router = APIRouter()
_redis = get_cache()


def _cache_get_or_set(key: str, fetch, ttl: int) -> dict | list:
    if _redis is not None:
        return _redis.get_or_set(key, fetch, ttl=ttl)
    return fetch()


@router.get("/calendar", response_model=ApiResponse)
def trade_calendar(
    start: str | None = Query(default=None, description="YYYY-MM-DD"),
    end: str | None = Query(default=None, description="YYYY-MM-DD"),
):
    ttl = int(os.getenv("FUND_NAV_TRADE_CAL_TTL_SEC", "300"))
    cache_key = f"trade:calendar:{start or ''}:{end or ''}"
    payload = _cache_get_or_set(cache_key, lambda: data.get_trade_calendar(start, end), ttl=ttl)
    return ApiResponse(ok=True, data=payload)


@router.get("/status", response_model=ApiResponse)
def trade_status(
    date: str | None = Query(default=None, description="YYYY-MM-DD"),
):
    tz = ZoneInfo("Asia/Shanghai")
    today = datetime.now(tz).strftime("%Y-%m-%d")
    target = date or today
    ttl = int(os.getenv("FUND_NAV_TRADE_CAL_TTL_SEC", "300"))
    cache_key = f"trade:status:{target}"

    def _compute():
        cal = set(data.get_trade_calendar())
        latest = data.get_latest_trading_date()
        return {
            "date": target,
            "is_trading_day": target in cal,
            "latest_trading_date": latest,
        }

    payload = _cache_get_or_set(cache_key, _compute, ttl=ttl)
    return ApiResponse(ok=True, data=payload)
