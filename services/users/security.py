import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from services.users.config import PASSWORD_ITERATIONS, PASSWORD_PEPPER, TOKEN_TTL_SEC


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        (password + PASSWORD_PEPPER).encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${_b64(salt)}${_b64(dk)}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        scheme, iterations, salt_b64, hash_b64 = hashed.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64 + "==")
        expected = base64.urlsafe_b64decode(hash_b64 + "==")
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            (password + PASSWORD_PEPPER).encode("utf-8"),
            salt,
            int(iterations),
        )
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def token_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=TOKEN_TTL_SEC)
