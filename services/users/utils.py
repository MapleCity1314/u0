import hashlib
import random
import string
from datetime import datetime, timedelta, timezone

from services.users.config import INVITE_TTL_DAYS


def generate_display_id() -> str:
    return "uu" + "".join(random.choices(string.digits, k=6))


def generate_invite_code() -> str:
    return "IV" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def invite_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=INVITE_TTL_DAYS)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
