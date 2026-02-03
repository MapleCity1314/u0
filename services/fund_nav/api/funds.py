from fastapi import APIRouter, HTTPException, Query

from services.logs.utils import log_event
from ..data import akshare_client as data
from ..models.schemas import ApiResponse, FundEstimate, FundSummary

router = APIRouter()


def _estimate(symbol: str, index_code: str | None = None, source: str = "auto") -> FundEstimate:
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
def fund_detail(code: str, index_code: str | None = None, source: str = "auto"):
    if source not in {"auto", "eastmoney", "model", "both"}:
        raise HTTPException(status_code=400, detail="invalid_source")
    try:
        est = _estimate(code, index_code=index_code, source=source)
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
