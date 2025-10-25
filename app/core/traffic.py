from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict

import h3

@dataclass
class TrafficProfile:
    base_multiplier: float = 1.0
    hourly_overrides: Dict[int, float] = field(default_factory=dict)
    zone_overrides: Dict[str, float] = field(default_factory=dict)

    def resolve(self, dt: datetime, zone: str | None) -> float:
        multiplier = self.base_multiplier
        hour = dt.hour
        if hour in self.hourly_overrides:
            multiplier *= self.hourly_overrides[hour]
        if zone and zone in self.zone_overrides:
            multiplier *= self.zone_overrides[zone]
        return max(multiplier, 0.2)

class TrafficModel:
    def __init__(self, resolution: int = 8) -> None:
        self._profiles: Dict[str, TrafficProfile] = {"default": TrafficProfile()}
        self.resolution = resolution

    def get(self, name: str = "default") -> TrafficProfile:
        if name not in self._profiles:
            self._profiles[name] = TrafficProfile()
        return self._profiles[name]

    def multiplier(self, lat: float, lon: float, moment: datetime | None = None, profile: str = "default") -> float:
        profile_obj = self.get(profile)
        dt = moment or datetime.utcnow()
        zone = h3.geo_to_h3(lat, lon, self.resolution) if h3 else None
        return profile_obj.resolve(dt, zone)

    def set_hourly_multiplier(self, hour: int, multiplier: float, profile: str = "default") -> None:
        hour = max(0, min(hour, 23))
        self.get(profile).hourly_overrides[hour] = multiplier

    def set_zone_multiplier(self, lat: float, lon: float, multiplier: float, profile: str = "default") -> str:
        zone = h3.geo_to_h3(lat, lon, self.resolution)
        self.get(profile).zone_overrides[zone] = multiplier
        return zone

    def snapshot(self) -> Dict[str, Dict[str, float]]:
        return {
            name: {
                "base_multiplier": profile.base_multiplier,
                "hourly_overrides": profile.hourly_overrides,
                "zone_overrides": profile.zone_overrides,
            }
            for name, profile in self._profiles.items()
        }
