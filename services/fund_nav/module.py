from fastapi import FastAPI

from .data import akshare_client
from .router import create_router


def register(app: FastAPI) -> None:
    app.include_router(create_router())
    akshare_client.start_background_refresh()
