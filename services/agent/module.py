from fastapi import FastAPI

from services.agent.api.router import router


def register(app: FastAPI) -> None:
    app.include_router(router)
