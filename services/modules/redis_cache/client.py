from __future__ import annotations

import json
import logging
import os
from typing import Any


logger = logging.getLogger("redis_cache")


def _json_default(value: Any) -> str:
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return str(value)


class RedisCache:
    def __init__(self, url: str, default_ttl: int = 30) -> None:
        self.url = url
        self.default_ttl = default_ttl
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import redis  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            logger.warning("redis import failed: %s", exc)
            return None
        try:
            self._client = redis.Redis.from_url(self.url, decode_responses=True)
            return self._client
        except Exception as exc:
            logger.warning("redis connect failed: %s", exc)
            self._client = None
            return None

    def get(self, key: str) -> Any | None:
        client = self._get_client()
        if client is None:
            return None
        try:
            value = client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as exc:
            logger.warning("redis get failed: %s", exc)
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> Any:
        client = self._get_client()
        if client is None:
            return value
        ttl_value = self.default_ttl if ttl is None else ttl
        try:
            payload = json.dumps(value, default=_json_default, ensure_ascii=False)
            client.setex(key, ttl_value, payload)
        except Exception as exc:
            logger.warning("redis set failed: %s", exc)
        return value

    def get_or_set(self, key: str, fetch, ttl: int | None = None) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = fetch()
        return self.set(key, value, ttl=ttl)


_CACHE = None


def get_cache() -> RedisCache | None:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    url = os.getenv("REDIS_URL")
    if not url:
        return None
    ttl = int(os.getenv("REDIS_DEFAULT_TTL_SEC", "30"))
    _CACHE = RedisCache(url, default_ttl=ttl)
    return _CACHE
