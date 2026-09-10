from fastapi.testclient import TestClient

from app.main import app

CLIENT_BASE_URL = "http://localhost"


def test_health() -> None:
    with TestClient(app, base_url=CLIENT_BASE_URL) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_versioned_health() -> None:
    with TestClient(app, base_url=CLIENT_BASE_URL) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
