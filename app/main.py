import os
import time
from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, Summary, generate_latest

from .core.engine import ETAEngine
from .core.traffic import TrafficModel
from .core.geodesy import haversine_km
from .models import (
    BatchETARequest,
    Diagnostics,
    ETARequest,
    MatrixETARequest,
    RouteETARequest,
    TrafficUpdate,
)

USE_CPP = os.getenv("USE_CPP") == "1"
LIB_PATH = os.getenv("ETA_LIB", "/app/libetacore.so")
CACHE_TTL = int(os.getenv("ETA_CACHE_TTL", "60"))

traffic_model = TrafficModel(resolution=int(os.getenv("H3_RESOLUTION", "8")))
engine = ETAEngine(traffic_model, use_cpp=USE_CPP, lib_path=LIB_PATH, cache_ttl_seconds=CACHE_TTL)

app = FastAPI(title="Realtime ETA", version="2.0.0")

REQUEST_COUNTER = Counter(
    "eta_requests_total", "Total ETA requests processed", labelnames=("endpoint", "profile")
)
LATENCY_SECONDS = Histogram(
    "eta_latency_seconds",
    "Latency for ETA computations",
    labelnames=("endpoint", "profile"),
    buckets=(0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0),
)
DISTANCE_KM = Summary("eta_distance_km", "Distance in kilometers for single ETA requests")
CACHE_HITS = Gauge("eta_cache_hits", "Total cache hits", multiprocess_mode="max")
CACHE_MISSES = Gauge("eta_cache_misses", "Total cache misses", multiprocess_mode="max")


def observe_cache() -> None:
    info = engine.cache_info()
    CACHE_HITS.set(info.get("hits", 0))
    CACHE_MISSES.set(info.get("misses", 0))


@app.get("/health")
def health() -> dict:
    observe_cache()
    return {
        "ok": True,
        "cache": engine.cache_info(),
        "cpp": USE_CPP,
    }


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    observe_cache()
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/eta")
def eta(req: ETARequest) -> dict:
    start = time.perf_counter()
    profile = req.profile
    REQUEST_COUNTER.labels(endpoint="single", profile=profile).inc()
    try:
        distance = haversine_km(
            req.origin.lat,
            req.origin.lon,
            req.destination.lat,
            req.destination.lon,
        )
        seconds = engine.eta_seconds(
            (req.origin.lat, req.origin.lon),
            (req.destination.lat, req.destination.lon),
            req.speed_kmh,
            profile,
            req.departure,
        )
    except Exception as exc:  # pragma: no cover - guard rail
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        LATENCY_SECONDS.labels(endpoint="single", profile=profile).observe(time.perf_counter() - start)
    DISTANCE_KM.observe(distance)
    return {
        "eta_seconds": seconds,
        "distance_km": distance,
        "profile": profile,
    }


@app.post("/eta/batch")
def eta_batch(req: BatchETARequest) -> dict:
    start = time.perf_counter()
    profile_counts: dict[str, int] = {}
    results: List[float] = []
    for item in req.requests:
        profile_counts[item.profile] = profile_counts.get(item.profile, 0) + 1
        results.append(
            engine.eta_seconds(
                (item.origin.lat, item.origin.lon),
                (item.destination.lat, item.destination.lon),
                item.speed_kmh,
                item.profile,
                item.departure,
            )
        )
    elapsed = time.perf_counter() - start
    for profile, count in profile_counts.items():
        REQUEST_COUNTER.labels(endpoint="batch", profile=profile).inc(count)
        LATENCY_SECONDS.labels(endpoint="batch", profile=profile).observe(elapsed)
    return {"eta_seconds": results, "count": len(results)}


@app.post("/eta/route")
def eta_route(req: RouteETARequest) -> dict:
    REQUEST_COUNTER.labels(endpoint="route", profile=req.profile).inc()
    total, legs = engine.route_eta(
        [(point.lat, point.lon) for point in req.waypoints],
        req.speed_kmh,
        req.profile,
        req.departure,
    )
    return {"total_seconds": total, "leg_seconds": legs}


@app.post("/eta/matrix")
def eta_matrix(req: MatrixETARequest) -> dict:
    REQUEST_COUNTER.labels(endpoint="matrix", profile=req.profile).inc(len(req.origins))
    matrix = engine.matrix_eta(
        [(p.lat, p.lon) for p in req.origins],
        [(p.lat, p.lon) for p in req.destinations],
        req.speed_kmh,
        req.profile,
    )
    return {"matrix": matrix}


@app.post("/traffic")
def update_traffic(update: TrafficUpdate) -> dict:
    if update.hour is not None:
        traffic_model.set_hourly_multiplier(update.hour, update.multiplier, update.profile)
        return {"profile": update.profile, "hour": update.hour, "multiplier": update.multiplier}
    assert update.lat is not None and update.lon is not None
    zone = traffic_model.set_zone_multiplier(update.lat, update.lon, update.multiplier, update.profile)
    return {"profile": update.profile, "zone": zone, "multiplier": update.multiplier}


@app.get("/diagnostics")
def diagnostics() -> Diagnostics:
    observe_cache()
    info = engine.cache_info()
    return Diagnostics(cache_hits=info.get("hits", 0), cache_misses=info.get("misses", 0), traffic_profiles=traffic_model.snapshot())