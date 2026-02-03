from __future__ import annotations

import time
from typing import Any, Dict, Tuple


class TTLCache:
    def __init__(self, default_ttl: int = 30) -> None:
        self.default_ttl = default_ttl
        self._store: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.time():
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> Any:
        ttl_value = self.default_ttl if ttl is None else ttl
        self._store[key] = (time.time() + ttl_value, value)
        return value

    def get_or_set(self, key: str, fetch, ttl: int | None = None) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = fetch()
        return self.set(key, value, ttl=ttl)
