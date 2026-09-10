import uuid

from fastapi.testclient import TestClient

from app.main import app

CLIENT_BASE_URL = "http://localhost"


def test_phase2_identity_tenancy_subscription_flow() -> None:
    email = f"phase2-{uuid.uuid4().hex}@example.test"
    password = "Phase2SecurePassword!2026"
    with TestClient(app, base_url=CLIENT_BASE_URL) as client:
        registered = client.post("/api/v1/auth/register", json={"email": email, "password": password, "first_name": "Test", "last_name": "Merchant", "phone": None})
        assert registered.status_code == 201
        user = registered.json()
        assert user["email"] == email

        logged_in = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert logged_in.status_code == 200
        tokens = logged_in.json()
        assert tokens["token_type"] == "bearer"
        assert tokens["access_token"]
        assert tokens["refresh_token"]

        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        me = client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["public_id"] == user["public_id"]

        plans = client.get("/api/v1/subscriptions/plans")
        assert plans.status_code == 200
        assert any(plan["slug"] == "free" for plan in plans.json())

        created = client.post("/api/v1/tenants", headers=headers, json={"name": "Phase 2 Shop"})
        assert created.status_code == 201
        tenant = created.json()
        assert tenant["role"] == "owner"

        tenants = client.get("/api/v1/tenants", headers=headers)
        assert tenants.status_code == 200
        assert any(item["public_id"] == tenant["public_id"] for item in tenants.json()["items"])

        subscription = client.get(f"/api/v1/subscriptions/{tenant['public_id']}", headers=headers)
        assert subscription.status_code == 200
        assert subscription.json()["plan"]["slug"] == "free"
        assert subscription.json()["status"] == "active"

        refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert refreshed.status_code == 200
        rotated = refreshed.json()
        assert rotated["refresh_token"] != tokens["refresh_token"]

        replay = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert replay.status_code == 401
