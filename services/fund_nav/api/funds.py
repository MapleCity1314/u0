import hashlib
import os
import pandas as pd

from fastapi import APIRouter, HTTPException, Query

from services.logs.utils import log_event
from services.modules.akshare.cache import TTLCache
from services.modules.redis_cache import get_cache
from ..data import akshare_client as data
from ..models.schemas import ApiResponse, FundEstimate, FundSummary, FundReturns
from ..core import estimator_rt
from ..core import rt_store

router = APIRouter()
_redis = get_cache()
_local_cache = TTLCache(default_ttl=int(os.getenv("FUND_NAV_ESTIMATE_TTL_SEC", "10")))


def _cache_get_or_set(key: str, fetch, ttl: int) -> dict | list:
    if _redis is not None:
        return _redis.get_or_set(key, fetch, ttl=ttl)
    return _local_cache.get_or_set(key, fetch, ttl=ttl)


def _estimate(
    symbol: str,
    index_code: str | None = None,
    source: str = "model",
    name_hint: str | None = None,
) -> FundEstimate:
    info = data.estimate_fund(
        symbol, index_code=index_code, source=source, name_hint=name_hint
    )
    return FundEstimate(**info)


@router.get("/search", response_model=ApiResponse)
def search(q: str = Query(min_length=1)):
    # Try to get comprehensive fund list first
    fund_df = data.get_all_fund_names()

    # Fall back to estimation data if comprehensive list is unavailable
    if fund_df is None:
        fund_df = data.get_fund_value_estimation()

    if fund_df is None:
        raise HTTPException(status_code=503, detail="fund_data_unavailable")

    code_col = None
    name_col = None
    for c in fund_df.columns:
        if "基金代码" in c or c.lower() in ("code", "基金代码"):
            code_col = c
        if "基金名称" in c or "基金简称" in c or c.lower() in ("name", "基金名称", "基金简称"):
            name_col = c
    if code_col is None or name_col is None:
        raise HTTPException(status_code=500, detail="search_fields_missing")

    q = q.strip()
    df = fund_df.copy()
    df[code_col] = df[code_col].astype(str)
    df[name_col] = df[name_col].astype(str)
    mask = df[code_col].str.contains(q, case=False, na=False) | df[name_col].str.contains(q, case=False, na=False)
    df = df[mask].head(20)

    out = []
    for _, row in df.iterrows():
        out.append(FundSummary(code=str(row[code_col]), name=str(row[name_col])))
    return ApiResponse(ok=True, data=[o.dict() for o in out])


@router.get("/{code}", response_model=ApiResponse)
def fund_detail(
    code: str,
    index_code: str | None = None,
    source: str = "model",
    name: str | None = None,
):
    raise HTTPException(status_code=410, detail="estimate_disabled_use_rt_batch")


@router.post("/estimate/rt", response_model=ApiResponse)
async def fund_estimate_rt(payload: dict):
    codes = payload.get("codes") if isinstance(payload, dict) else None
    if not isinstance(codes, list) or not codes:
        raise HTTPException(status_code=400, detail="invalid_codes")

    cleaned = [str(c) for c in codes]
    cache_ttl = int(os.getenv("FUND_NAV_RT_TTL_SEC", "15"))
    key_seed = ",".join(sorted(set(cleaned)))
    cache_key = f"fund:estimate:rt:{hashlib.md5(key_seed.encode('utf-8')).hexdigest()}"

    cached = None
    if _redis is not None:
        cached = _redis.get(cache_key)
    if cached is None:
        cached = _local_cache.get(cache_key)
    if cached is not None:
        return ApiResponse(ok=True, data=cached)

    data = await estimator_rt.estimate_many(cleaned)

    try:
        rt_store.store_snapshot(data)
    except Exception:
        pass

    if _redis is not None:
        _redis.set(cache_key, data, ttl=cache_ttl)
    else:
        _local_cache.set(cache_key, data, ttl=cache_ttl)

    return ApiResponse(ok=True, data=data)



def _return_since(df, target_date):
    if df is None or df.empty:
        return None
    subset = df[df["date"] <= target_date]
    if subset.empty:
        return None
    last_nav = float(df["nav"].iloc[-1])
    base_nav = float(subset["nav"].iloc[-1])
    if base_nav <= 0:
        return None
    return (last_nav / base_nav) - 1.0


def _calc_returns(code: str) -> FundReturns:
    df = data.get_fund_nav_daily(code)
    if df is None or df.empty:
        return FundReturns(code=code, nav=None, nav_date=None, returns={})
    df = df.sort_values("date")
    last_date = df["date"].iloc[-1]
    last_nav = float(df["nav"].iloc[-1])

    day = pd.Timedelta(days=1)
    periods = {
        "week": 7,
        "month": 30,
        "quarter": 90,
        "halfYear": 180,
        "year1": 365,
        "year2": 365 * 2,
        "year3": 365 * 3,
        "year5": 365 * 5,
    }

    returns = {}
    for key, days in periods.items():
        returns[key] = _return_since(df, last_date - pd.Timedelta(days=days))

    ytd_start = pd.Timestamp(year=last_date.year, month=1, day=1)
    returns["ytd"] = _return_since(df, ytd_start)

    inception_nav = float(df["nav"].iloc[0])
    if inception_nav > 0:
        returns["inception"] = (last_nav / inception_nav) - 1.0
    else:
        returns["inception"] = None

    return FundReturns(
        code=code,
        nav=last_nav,
        nav_date=last_date.strftime("%Y-%m-%d"),
        returns=returns,
    )


@router.get("/{code}/curve", response_model=ApiResponse)
def fund_curve(code: str, days: int = Query(default=7, ge=1, le=60)):
    try:
        ttl = int(os.getenv("FUND_NAV_CURVE_TTL_SEC", "30"))
        cache_key = f"fund:curve:{code}:{days}"
        payload = _cache_get_or_set(
            cache_key,
            lambda: data.estimate_curve(code, data.get_fund_nav_recent(code, days=days)),
            ttl=ttl,
        )
        return ApiResponse(ok=True, data=payload)
    except Exception as exc:
        log_event("error", "fund_nav.api", "curve_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="curve_failed")


@router.get("/{code}/returns", response_model=ApiResponse)
def fund_returns(code: str):
    try:
        ttl = int(os.getenv("FUND_NAV_RETURNS_TTL_SEC", "300"))
        cache_key = f"fund:returns:{code}"
        payload = _cache_get_or_set(
            cache_key,
            lambda: _calc_returns(code).dict(),
            ttl=ttl,
        )
        return ApiResponse(ok=True, data=payload)
    except Exception as exc:
        log_event("error", "fund_nav.api", "returns_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="returns_failed")


@router.get("/{code}/curve", response_model=ApiResponse)
def fund_curve(code: str, days: int = Query(default=7, ge=1, le=60)):
    try:
        history = data.get_fund_nav_recent(code, days=days)
        curve = data.estimate_curve(code, history)
        return ApiResponse(ok=True, data=curve)
    except Exception as exc:
        log_event("error", "fund_nav.api", "curve_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="curve_failed")
