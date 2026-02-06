from fastapi import APIRouter

from .api import funds, market


def create_router() -> APIRouter:
    router = APIRouter()
    router.include_router(funds.router, prefix="/api/funds", tags=["funds"])
    router.include_router(market.router, prefix="/api/market", tags=["market"])
    return router
