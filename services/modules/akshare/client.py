from __future__ import annotations

import os
import threading
from typing import Any

import akshare as ak

from .cache import TTLCache

REQUEST_TIMEOUT = 60
DEFAULT_TTL_SEC = int(os.getenv("AKSHARE_CACHE_TTL_SEC", "30"))

_cache = TTLCache(DEFAULT_TTL_SEC)


class TimeoutError(Exception):
    pass


def has_func(name: str) -> bool:
    return hasattr(ak, name)


def call_with_timeout(func, args=(), kwargs=None, timeout=REQUEST_TIMEOUT) -> Any:
    if kwargs is None:
        kwargs = {}

    result = [None]
    exception = [None]

    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - passthrough
            exception[0] = exc

    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        raise TimeoutError(f"Operation timed out after {timeout} seconds")
    if exception[0] is not None:
        raise exception[0]
    return result[0]


def _cache_key(name: str, kwargs: dict | None) -> str:
    if not kwargs:
        return name
    parts = [name]
    for key in sorted(kwargs.keys()):
        parts.append(f"{key}={kwargs[key]}")
    return "|".join(parts)


def call(name: str, *, kwargs: dict | None = None, timeout: int = REQUEST_TIMEOUT) -> Any:
    func = getattr(ak, name)
    return call_with_timeout(func, kwargs=kwargs, timeout=timeout)


def cached_call(
    name: str,
    *,
    kwargs: dict | None = None,
    timeout: int = REQUEST_TIMEOUT,
    ttl: int | None = None,
) -> Any:
    if ttl is not None and ttl <= 0:
        return call(name, kwargs=kwargs, timeout=timeout)

    key = _cache_key(name, kwargs)

    def fetch():
        return call(name, kwargs=kwargs, timeout=timeout)

    return _cache.get_or_set(key, fetch, ttl=ttl)
