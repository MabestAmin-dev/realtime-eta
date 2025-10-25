# Realtime ETA (starter)

FastAPI service with an optional C++ core. Uses simple haversine + average speed as a baseline with
hooks to swap in an H3-based implementation.

## Endpoints
- `GET /health` – liveness
- `POST /eta` – JSON: `{"origin":{"lat":..,"lon":..}, "destination":{"lat":..,"lon":..}}` → ETA seconds

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

## CI
GitHub Actions workflow runs lint + tests.