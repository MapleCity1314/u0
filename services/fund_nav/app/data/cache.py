import time
from typing import Callable, Optional, TypeVar

T = TypeVar("T")


class TTLCache:
    def __init__(self, ttl_sec: int) -> None:
        self.ttl_sec = ttl_sec
        self._value: Optional[T] = None
        self._ts: float = 0.0

    def get(self) -> Optional[T]:
        if self._value is None:
            return None
        if time.time() - self._ts > self.ttl_sec:
            return None
        return self._value

    def set(self, value: T) -> T:
        self._value = value
        self._ts = time.time()
        return value

    def get_or_set(self, fn: Callable[[], T]) -> T:
        cached = self.get()
        if cached is not None:
            return cached
        return self.set(fn())
