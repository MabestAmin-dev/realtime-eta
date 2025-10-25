import os
import math
import time
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import PlainTextResponse

USE_CPP = os.getenv("USE_CPP") == "1"
LIB_PATH = os.getenv("ETA_LIB", "/app/libetacore.so")

# Metrics
req_counter = Counter('eta_requests_total', 'Total ETA requests')
latency_hist = Histogram('eta_latency_ms', 'ETA compute latency (ms)')

class Point(BaseModel):
    lat: float
    lon: float

class ETARequest(BaseModel):
    origin: Point
    destination: Point
    speed_kmh: Optional[float] = 30.0

app = FastAPI()

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dl/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def eta_seconds_py(o: Point, d: Point, speed_kmh: float) -> float:
    dist_km = haversine_km(o.lat, o.lon, d.lat, d.lon)
    hours = dist_km / max(speed_kmh, 1e-3)
    return hours * 3600

try:
    if USE_CPP:
        import ctypes
        lib = ctypes.CDLL(LIB_PATH)
        lib.eta_seconds.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double]
        lib.eta_seconds.restype = ctypes.c_double
        def eta_seconds(o: Point, d: Point, speed_kmh: float) -> float:
            return lib.eta_seconds(o.lat, o.lon, d.lat, d.lon, speed_kmh)
    else:
        def eta_seconds(o: Point, d: Point, speed_kmh: float) -> float:
            return eta_seconds_py(o, d, speed_kmh)
except Exception as e:
    # Fallback if C++ load fails
    def eta_seconds(o: Point, d: Point, speed_kmh: float) -> float:
        return eta_seconds_py(o, d, speed_kmh)

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest())

@app.post("/eta")
def eta(req: ETARequest):
    req_counter.inc()
    t0 = time.time()
    try:
        seconds = eta_seconds(req.origin, req.destination, req.speed_kmh or 30.0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        latency_hist.observe((time.time() - t0) * 1000.0)
    return {"eta_seconds": seconds}