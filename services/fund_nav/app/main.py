import logging
import os
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import auth, funds, health, portfolio, positions, watchlist
from .core.config import APP_NAME, CORS_ALLOW_ORIGINS, MEDIA_BASE_PATH, MEDIA_DIR
from .models.schemas import ApiResponse, ErrorResponse

app = FastAPI(title=APP_NAME)

os.makedirs(MEDIA_DIR, exist_ok=True)
app.mount(MEDIA_BASE_PATH, StaticFiles(directory=MEDIA_DIR), name="media")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in CORS_ALLOW_ORIGINS if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(funds.router, prefix="/api/funds", tags=["funds"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["watchlist"])
app.include_router(positions.router, prefix="/api/positions", tags=["positions"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(health.router, prefix="/api/health", tags=["health"])

logger = logging.getLogger(APP_NAME)
logging.basicConfig(level=logging.INFO)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    logger.info("%s %s %s %dms", request.method, request.url.path, response.status_code, duration_ms)
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code = str(exc.detail) if exc.detail else "http_error"
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(ok=False, error=ErrorResponse(code=code, message=code)).dict(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content=ApiResponse(ok=False, error=ErrorResponse(code="internal_error", message=str(exc))).dict(),
    )
