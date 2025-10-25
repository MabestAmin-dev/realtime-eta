from fastapi.testclient import TestClient

from main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True


def test_single_eta_roundtrip() -> None:
    client = TestClient(app)
    payload = {
        "origin": {"lat": 52.37, "lon": 4.89},
        "destination": {"lat": 52.52, "lon": 13.4},
        "speed_kmh": 80,
        "profile": "default",
    }
    response = client.post("/eta", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["eta_seconds"] > 0
    assert body["distance_km"] > 0


def test_batch_eta() -> None:
    client = TestClient(app)
    payload = {
        "requests": [
            {
                "origin": {"lat": 52.37, "lon": 4.89},
                "destination": {"lat": 52.52, "lon": 13.4},
                "speed_kmh": 80,
                "profile": "default",
            },
            {
                "origin": {"lat": 37.77, "lon": -122.42},
                "destination": {"lat": 37.78, "lon": -122.41},
                "speed_kmh": 35,
                "profile": "default",
            },
        ]
    }
    response = client.post("/eta/batch", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["eta_seconds"]) == 2