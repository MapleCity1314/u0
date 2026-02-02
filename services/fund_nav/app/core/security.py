import hashlib
import secrets
import time
from dataclasses import dataclass
from typing import Optional

from .config import TOKEN_TTL_SEC


@dataclass
class Token:
    value: str
    user_id: str
    expires_at: float


class TokenIssuer:
    def __init__(self) -> None:
        self._tokens: dict[str, Token] = {}

    def issue(self, user_id: str) -> Token:
        value = secrets.token_urlsafe(24)
        expires_at = time.time() + TOKEN_TTL_SEC
        token = Token(value=value, user_id=user_id, expires_at=expires_at)
        self._tokens[value] = token
        return token

    def validate(self, value: str) -> Optional[Token]:
        token = self._tokens.get(value)
        if token is None:
            return None
        if token.expires_at < time.time():
            self._tokens.pop(value, None)
            return None
        return token


def hash_password(password: str) -> str:
    salt = secrets.token_hex(8)
    digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def verify_password(stored: str, password: str) -> bool:
    if "$" not in stored:
        return False
    salt, digest = stored.split("$", 1)
    check = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return secrets.compare_digest(digest, check)
