from fastapi import APIRouter, Depends

from ..core.state import store
from ..models.schemas import ApiResponse, PositionResponse, PositionUpdateRequest
from .auth import get_current_user

router = APIRouter()


@router.get("/", response_model=ApiResponse)
def list_positions(user=Depends(get_current_user)):
    positions = store.list_positions(user.id)
    data = [
        PositionResponse(code=p["code"], units=p["units"], cost=p.get("cost")).dict()
        for p in positions
    ]
    return ApiResponse(ok=True, data=data)


@router.put("/{code}", response_model=ApiResponse)
def upsert_position(code: str, req: PositionUpdateRequest, user=Depends(get_current_user)):
    entry = store.upsert_position(user.id, code, units=req.units, cost=req.cost)
    data = PositionResponse(code=entry["code"], units=entry["units"], cost=entry.get("cost")).dict()
    return ApiResponse(ok=True, data=data)
