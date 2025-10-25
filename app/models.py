from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

class Point(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)

class ETARequest(BaseModel):
    origin: Point
    destination: Point
    speed_kmh: float = Field(30.0, gt=0)
    profile: str = Field("default", min_length=1, max_length=32)
    departure: Optional[datetime] = None

class BatchETARequest(BaseModel):
    requests: List[ETARequest] = Field(..., min_length=1, max_length=100)

class RouteETARequest(BaseModel):
    waypoints: List[Point] = Field(..., min_length=2, max_length=50)
    speed_kmh: float = Field(30.0, gt=0)
    profile: str = Field("default", min_length=1, max_length=32)
    departure: Optional[datetime] = None

class MatrixETARequest(BaseModel):
    origins: List[Point] = Field(..., min_length=1, max_length=50)
    destinations: List[Point] = Field(..., min_length=1, max_length=50)
    speed_kmh: float = Field(30.0, gt=0)
    profile: str = Field("default", min_length=1, max_length=32)

class TrafficUpdate(BaseModel):
    profile: str = Field("default", min_length=1, max_length=32)
    hour: Optional[int] = Field(None, ge=0, le=23)
    multiplier: float = Field(..., gt=0)
    lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    lon: Optional[float] = Field(None, ge=-180.0, le=180.0)

    @field_validator("lat")
    @classmethod
    def validate_pair(cls, v: Optional[float], values: dict) -> Optional[float]:
        lon = values.get("lon")
        hour = values.get("hour")
        if v is not None and lon is None:
            raise ValueError("longitude required when latitude is set")
        if lon is not None and v is None:
            raise ValueError("latitude required when longitude is set")
        if hour is None and lon is None:
            raise ValueError("provide either an hour or lat/lon pair")
        return v

class Diagnostics(BaseModel):
    cache_hits: int
    cache_misses: int
    traffic_profiles: dict
