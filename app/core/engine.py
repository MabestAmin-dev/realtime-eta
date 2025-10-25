from __future__ import annotations

import ctypes
import math
import os
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Iterable, List, Sequence, Tuple

from .cache import TTLFunctionCache
from .geodesy import distance_matrix, haversine_km
from .traffic import TrafficModel

Point = Tuple[float, float]

class ETAEngine:
    def __init__(
        self,
        traffic: TrafficModel,
        use_cpp: bool = False,
        lib_path: str | None = None,
        cache_ttl_seconds: int = 30,
    ) -> None:
        self.traffic = traffic
        self._cache = TTLFunctionCache[str, float](maxsize=4096, ttl_seconds=cache_ttl_seconds)
        self._lib = self._load_cpp(lib_path) if use_cpp else None

    @staticmethod
    def _load_cpp(lib_path: str | None) -> ctypes.CDLL | None:
        path = lib_path or os.getenv("ETA_LIB", "/app/libetacore.so")
        if not os.path.exists(path):
            return None
        lib = ctypes.CDLL(path)
        lib.eta_seconds.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double]
        lib.eta_seconds.restype = ctypes.c_double
        return lib

    @staticmethod
    def _sanitize_speed(speed_kmh: float) -> float:
        return max(speed_kmh, 1e-3)

    def _key(self, origin: Point, destination: Point, speed: float, profile: str) -> str:
        return f"{origin[0]:.4f}:{origin[1]:.4f}:{destination[0]:.4f}:{destination[1]:.4f}:{speed:.2f}:{profile}"

    def _raw_eta(self, origin: Point, destination: Point, speed_kmh: float) -> float:
        if self._lib:
            return float(
                self._lib.eta_seconds(origin[0], origin[1], destination[0], destination[1], self._sanitize_speed(speed_kmh))
            )
        distance = haversine_km(origin[0], origin[1], destination[0], destination[1])
        hours = distance / self._sanitize_speed(speed_kmh)
        return hours * 3600.0

    def eta_seconds(
        self,
        origin: Point,
        destination: Point,
        speed_kmh: float,
        profile: str = "default",
        departure: datetime | None = None,
    ) -> float:
        def compute(_: str) -> float:
            multiplier = self.traffic.multiplier(origin[0], origin[1], departure, profile)
            adjusted_speed = speed_kmh * multiplier
            return self._raw_eta(origin, destination, adjusted_speed)

        key = self._key(origin, destination, speed_kmh, profile)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        value = compute(key)
        self._cache.set(key, value)
        return value

    def batch_eta(
        self,
        pairs: Iterable[Tuple[Point, Point]],
        speed_kmh: float,
        profile: str = "default",
        departure: datetime | None = None,
    ) -> List[float]:
        return [self.eta_seconds(origin, destination, speed_kmh, profile, departure) for origin, destination in pairs]

    def route_eta(
        self,
        waypoints: Sequence[Point],
        speed_kmh: float,
        profile: str = "default",
        departure: datetime | None = None,
    ) -> Tuple[float, List[float]]:
        if len(waypoints) < 2:
            raise ValueError("At least two waypoints required")
        leg_etas: List[float] = []
        total = 0.0
        current_departure = departure or datetime.utcnow()
        for i in range(len(waypoints) - 1):
            leg = self.eta_seconds(waypoints[i], waypoints[i + 1], speed_kmh, profile, current_departure)
            leg_etas.append(leg)
            total += leg
            current_departure = current_departure + timedelta(seconds=leg)
        return total, leg_etas

    def matrix_eta(
        self,
        origins: Sequence[Point],
        destinations: Sequence[Point],
        speed_kmh: float,
        profile: str = "default",
    ) -> List[List[float]]:
        distances = distance_matrix(origins, destinations)
        matrix: List[List[float]] = []
        for origin, row in zip(origins, distances):
            multiplier = self.traffic.multiplier(origin[0], origin[1], profile=profile)
            sanitized_speed = self._sanitize_speed(speed_kmh * multiplier)
            seconds_per_km = 3600.0 / sanitized_speed
            matrix.append([km * seconds_per_km for km in row])
        return matrix

    def cache_info(self) -> dict[str, int]:
        hits, misses = self._cache.info()
        return {"hits": hits, "misses": misses}
