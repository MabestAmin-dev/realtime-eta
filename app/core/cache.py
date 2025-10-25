from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable, Generic, Optional, Tuple, TypeVar

from cachetools import TTLCache

K = TypeVar("K")
V = TypeVar("V")

@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0

class TTLFunctionCache(Generic[K, V]):
    def __init__(self, maxsize: int = 1024, ttl_seconds: int = 60) -> None:
        self._cache: TTLCache[K, V] = TTLCache(maxsize=maxsize, ttl=ttl_seconds)
        self._lock = threading.Lock()
        self.stats = CacheStats()

    def cached(self, fn: Callable[[K], V]) -> Callable[[K], V]:
        def wrapper(key: K) -> V:
            with self._lock:
                try:
                    value = self._cache[key]
                    self.stats.hits += 1
                    return value
                except KeyError:
                    self.stats.misses += 1
            value = fn(key)
            with self._lock:
                self._cache[key] = value
            return value

        return wrapper

    def get(self, key: K) -> Optional[V]:
        with self._lock:
            try:
                self.stats.hits += 1
                return self._cache[key]
            except KeyError:
                self.stats.misses += 1
                return None

    def set(self, key: K, value: V) -> None:
        with self._lock:
            self._cache[key] = value

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self.stats = CacheStats()

    def info(self) -> Tuple[int, int]:
        with self._lock:
            return self.stats.hits, self.stats.misses
