import logging
import sys
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from services.fund_nav.core.config import APP_NAME, CORS_ALLOW_ORIGINS
from services.fund_nav.models.schemas import ApiResponse, ErrorResponse
from services.logs.utils import log_event
from services.server.registry import load_modules

app = FastAPI(title="services")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in CORS_ALLOW_ORIGINS if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_modules(app)

logger = logging.getLogger(APP_NAME)
logging.basicConfig(level=logging.INFO)


@app.get("/health")
def health():
    return {"ok": True}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    logger.info("%s %s %s %dms", request.method, request.url.path, response.status_code, duration_ms)
    log_event(
        "info",
        "http",
        f"{request.method} {request.url.path}",
        request_id=request.headers.get("x-request-id"),
        extra=f"status={response.status_code},duration_ms={duration_ms}",
    )
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code = str(exc.detail) if exc.detail else "http_error"
    log_event(
        "error",
        "http",
        f"HTTPException {request.method} {request.url.path}",
        request_id=request.headers.get("x-request-id"),
        error=code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(ok=False, error=ErrorResponse(code=code, message=code)).dict(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    log_event(
        "error",
        "http",
        f"Unhandled {request.method} {request.url.path}",
        request_id=request.headers.get("x-request-id"),
        error=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content=ApiResponse(ok=False, error=ErrorResponse(code="internal_error", message=str(exc))).dict(),
    )
