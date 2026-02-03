from fastapi import APIRouter

from .api import funds


def create_router() -> APIRouter:
    router = APIRouter()
    router.include_router(funds.router, prefix="/api/funds", tags=["funds"])
    return router
