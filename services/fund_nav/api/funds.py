import os

from fastapi import APIRouter, HTTPException, Query

from services.logs.utils import log_event
from services.modules.akshare.cache import TTLCache
from services.modules.redis_cache import get_cache
from ..data import akshare_client as data
from ..models.schemas import ApiResponse, FundEstimate, FundSummary

router = APIRouter()
_redis = get_cache()
_local_cache = TTLCache(default_ttl=int(os.getenv("FUND_NAV_ESTIMATE_TTL_SEC", "10")))


def _cache_get_or_set(key: str, fetch, ttl: int) -> dict | list:
    if _redis is not None:
        return _redis.get_or_set(key, fetch, ttl=ttl)
    return _local_cache.get_or_set(key, fetch, ttl=ttl)


def _estimate(symbol: str, index_code: str | None = None, source: str = "model") -> FundEstimate:
    info = data.estimate_fund(symbol, index_code=index_code, source=source)
    return FundEstimate(**info)


@router.get("/search", response_model=ApiResponse)
def search(q: str = Query(min_length=1)):
    est_df = data.get_fund_value_estimation()
    if est_df is None:
        raise HTTPException(status_code=503, detail="estimation_source_unavailable")

    code_col = None
    name_col = None
    for c in est_df.columns:
        if "基金代码" in c or c.lower() in ("code", "基金代码"):
            code_col = c
        if "基金名称" in c or c.lower() in ("name", "基金名称"):
            name_col = c
    if code_col is None or name_col is None:
        raise HTTPException(status_code=500, detail="search_fields_missing")

    q = q.strip()
    df = est_df.copy()
    df[code_col] = df[code_col].astype(str)
    df[name_col] = df[name_col].astype(str)
    mask = df[code_col].str.contains(q) | df[name_col].str.contains(q)
    df = df[mask].head(20)

    out = []
    for _, row in df.iterrows():
        out.append(FundSummary(code=str(row[code_col]), name=str(row[name_col])))
    return ApiResponse(ok=True, data=[o.dict() for o in out])


@router.get("/{code}", response_model=ApiResponse)
def fund_detail(code: str, index_code: str | None = None, source: str = "model"):
    if source not in {"auto", "eastmoney", "model", "both"}:
        raise HTTPException(status_code=400, detail="invalid_source")
    try:
        ttl = int(os.getenv("FUND_NAV_ESTIMATE_TTL_SEC", "10"))
        cache_key = f"fund:estimate:{code}:{index_code or ''}:{source}"
        payload = _cache_get_or_set(
            cache_key,
            lambda: _estimate(code, index_code=index_code, source=source).dict(),
            ttl=ttl,
        )
        est = FundEstimate(**payload)
        if source == "eastmoney" and est.est_return_em is None:
            raise HTTPException(status_code=503, detail="eastmoney_unavailable")
        if source == "model" and est.est_return_model is None:
            raise HTTPException(status_code=503, detail="model_unavailable")
        return ApiResponse(ok=True, data=est.dict())
    except HTTPException:
        raise
    except Exception as e:
        log_event("error", "fund_nav.api", "estimate_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"estimate_failed:{str(e)[:80]}")


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


@router.get("/{code}/curve", response_model=ApiResponse)
def fund_curve(code: str, days: int = Query(default=7, ge=1, le=60)):
    try:
        history = data.get_fund_nav_recent(code, days=days)
        curve = data.estimate_curve(code, history)
        return ApiResponse(ok=True, data=curve)
    except Exception as exc:
        log_event("error", "fund_nav.api", "curve_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="curve_failed")
