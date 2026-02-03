from fastapi import FastAPI

from .router import create_router


def register(app: FastAPI) -> None:
    app.include_router(create_router())
