import os
from pathlib import Path

from dotenv import load_dotenv


def _load_env() -> None:
    root = Path(__file__).resolve().parents[3]
    env_path = root / ".env"
    if env_path.exists():
        load_dotenv(env_path)


_load_env()

APP_NAME = "fund_nav"
ENV = os.getenv("FUND_NAV_ENV", "dev")

# Storage
STORE_BACKEND = os.getenv("FUND_NAV_STORE_BACKEND", "sqlite")
DB_PATH = os.getenv("FUND_NAV_DB_PATH", "data/fund_nav.db")

# Invite system
INITIAL_INVITE_CODE = os.getenv("FUND_NAV_INITIAL_INVITE_CODE", "")
INVITE_DEFAULT_USES = int(os.getenv("FUND_NAV_INVITE_DEFAULT_USES", "1"))
INVITE_MAX_USES = int(os.getenv("FUND_NAV_INVITE_MAX_USES", "50"))
INVITE_TTL_SEC = int(os.getenv("FUND_NAV_INVITE_TTL_SEC", str(7 * 24 * 3600)))

# Caching
CACHE_TTL_SEC = int(os.getenv("FUND_NAV_CACHE_TTL_SEC", "30"))

# Auth
TOKEN_TTL_SEC = int(os.getenv("FUND_NAV_TOKEN_TTL_SEC", "86400"))

# Positions
POSITION_DEFAULT_UNITS = float(os.getenv("FUND_NAV_POSITION_DEFAULT_UNITS", "100"))

# CORS
CORS_ALLOW_ORIGINS = os.getenv("FUND_NAV_CORS_ALLOW_ORIGINS", "http://localhost:3000").split(",")

# Media uploads
MEDIA_DIR = os.getenv("FUND_NAV_MEDIA_DIR", "data/media")
MEDIA_BASE_PATH = os.getenv("FUND_NAV_MEDIA_BASE_PATH", "/media")
PUBLIC_BASE_URL = os.getenv("FUND_NAV_PUBLIC_BASE_URL", "")
