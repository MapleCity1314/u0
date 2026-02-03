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

# CORS
CORS_ALLOW_ORIGINS = os.getenv("FUND_NAV_CORS_ALLOW_ORIGINS", "http://localhost:3000").split(",")
