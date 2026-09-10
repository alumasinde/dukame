from fastapi.testclient import TestClient

from app.main import app

CLIENT_BASE_URL = "http://localhost"


def test_health() -> None:
    with TestClient(app, base_url=CLIENT_BASE_URL) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_versioned_api() -> None:
    with TestClient(app, base_url=CLIENT_BASE_URL) as client:
        response = client.get("/api/v1")
    assert response.status_code == 200
    assert response.json()["service"] == "DukaMe API"
    assert response.json()["version"] == "0.1.0"


def test_request_id_is_generated_and_returned() -> None:
    with TestClient(app, base_url=CLIENT_BASE_URL) as client:
        response = client.get(
            "/api/v1/health",
            headers={"X-Request-ID": "phase1-test-id"},
        )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "phase1-test-id"
