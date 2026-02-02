from fastapi import APIRouter, Depends, HTTPException

from ..core.state import store
from ..models.schemas import ApiResponse, FundSummary, WatchlistResponse
from .auth import get_current_user
from .funds import _estimate

router = APIRouter()


@router.get("/", response_model=ApiResponse)
def list_watch(user=Depends(get_current_user)):
    codes = store.list_watch(user.id)
    funds: list[FundSummary] = []
    for code in codes:
        try:
            est = _estimate(code)
            funds.append(
                FundSummary(
                    code=code,
                    name=est.name,
                    est_return=est.est_return,
                    source=est.source,
                )
            )
        except Exception:
            funds.append(FundSummary(code=code))
    return ApiResponse(ok=True, data=WatchlistResponse(funds=funds).dict())


@router.post("/{code}", response_model=ApiResponse)
def add_watch(code: str, user=Depends(get_current_user)):
    store.add_watch(user.id, code)
    return ApiResponse(ok=True, data={"code": code})


@router.delete("/{code}", response_model=ApiResponse)
def remove_watch(code: str, user=Depends(get_current_user)):
    store.remove_watch(user.id, code)
    return ApiResponse(ok=True, data={"code": code})
