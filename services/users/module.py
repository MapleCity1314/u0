from fastapi import FastAPI

from services.users.api.routes import router


def register(app: FastAPI) -> None:
    app.include_router(router, prefix="/api", tags=["users"])
