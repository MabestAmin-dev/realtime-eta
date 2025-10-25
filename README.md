# Realtime ETA (v2)

FastAPI service with modular ETA engine, optional C++ acceleration, H3-aware traffic modelling, and Prometheus metrics.

## Endpoints
- `GET /health` – liveness + cache stats + C++ indicator.
- `POST /eta` – Single ETA with traffic profile + optional departure timestamp.
- `POST /eta/batch` – Compute multiple ETAs in one request.
- `POST /eta/route` – Aggregated travel time across ordered waypoints.
- `POST /eta/matrix` – Origin/destination matrix (useful for dispatch batching).
- `POST /traffic` – Update hourly or geo (H3) traffic multipliers.
- `GET /diagnostics` – Cache hit/miss counters + profile snapshot.
- `GET /metrics` – Prometheus metrics (latency, cache, request counts).

## Run (Python-only fallback)
```bash
cd app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## Optional: C++ core
- Build the C++ library with CMake to produce `libetacore.so`
- Set `USE_CPP=1` to make the FastAPI service load the shared library via `ctypes`
- Use `ETA_LIB` to override the shared library path.

## CI
GitHub Actions workflow runs lint + tests.

## Architecture
- `core/engine.py` encapsulates ETA calculations, caching, routing, and matrix helpers.
- `core/traffic.py` stores dynamic traffic profiles with hourly + H3 zone overrides.
- `core/cache.py` provides thread-safe TTL cache instrumentation.
- `models.py` defines Pydantic schemas shared across endpoints.

## Telemetry
- Prometheus metrics for request counts, latency histograms, cache stats, and distances.
- Diagnostics endpoint returns structured cache + profile data for dashboards.