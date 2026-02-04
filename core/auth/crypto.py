import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def hash_password(password: str, pepper: str, iterations: int) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        (password + pepper).encode("utf-8"),
        salt,
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${_b64(salt)}${_b64(dk)}"


def verify_password(password: str, hashed: str, pepper: str) -> bool:
    try:
        scheme, iterations, salt_b64, hash_b64 = hashed.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64 + "==")
        expected = base64.urlsafe_b64decode(hash_b64 + "==")
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            (password + pepper).encode("utf-8"),
            salt,
            int(iterations),
        )
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def token_expires_at(ttl_sec: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=ttl_sec)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
