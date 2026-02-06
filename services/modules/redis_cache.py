from __future__ import annotations

from typing import Any


class _NoopCache:
    def get(self, key: str) -> Any | None:
        return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> Any:
        return value

    def get_or_set(self, key: str, fetch, ttl: int | None = None) -> Any:
        return fetch()


def get_cache():
    # Return Redis cache if configured; default is None (noop).
    return None
