import uuid

from fastapi.testclient import TestClient

from app.main import app

CLIENT_BASE_URL = "http://localhost"


def test_phase2_identity_tenancy_subscription_flow() -> None:
    email = f"phase2-{uuid.uuid4().hex}@example.com"
    password = "Phase2SecurePassword!2026"
    with TestClient(app, base_url=CLIENT_BASE_URL) as client:
        registered = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "first_name": "Test",
                "last_name": "Merchant",
                "phone": None,
            },
        )
        assert registered.status_code == 201, registered.text
        user = registered.json()
        assert user["email"] == email
        assert user["onboarding"]["completed"] is False
        assert user["onboarding"]["current_step"] == "shop_setup"
        assert user["onboarding"]["total_steps"] == 3

        logged_in = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert logged_in.status_code == 200, logged_in.text
        tokens = logged_in.json()
        assert tokens["token_type"] == "bearer"
        assert tokens["access_token"]
        assert tokens["refresh_token"]

        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        me = client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200, me.text
        assert me.json()["public_id"] == user["public_id"]
        assert me.json()["onboarding"]["completed"] is False
        assert me.json()["onboarding"]["total_steps"] == 3

        onboarding_status = client.get("/api/v1/onboarding/status", headers=headers)
        assert onboarding_status.status_code == 200, onboarding_status.text
        assert onboarding_status.json()["completed"] is False
        assert onboarding_status.json()["current_step"] == "shop_setup"

        completed = client.post(
            "/api/v1/onboarding/shop",
            headers=headers,
            json={
                "shop_name": "Phase 2 Shop",
                "shop_slug": f"phase2shop{uuid.uuid4().hex[:8]}",
            },
        )
        assert completed.status_code == 201, completed.text
        onboarding = completed.json()
        assert onboarding["completed"] is True
        assert onboarding["tenant_public_id"]

        me_after_onboarding = client.get("/api/v1/auth/me", headers=headers)
        assert me_after_onboarding.status_code == 200, me_after_onboarding.text
        assert me_after_onboarding.json()["onboarding"]["completed"] is True
        assert (
            me_after_onboarding.json()["onboarding"]["tenant_public_id"]
            == onboarding["tenant_public_id"]
        )

        plans = client.get("/api/v1/subscriptions/plans")
        assert plans.status_code == 200, plans.text
        assert any(plan["slug"] == "free" for plan in plans.json())

        tenants = client.get("/api/v1/tenants", headers=headers)
        assert tenants.status_code == 200, tenants.text
        assert any(
            item["public_id"] == onboarding["tenant_public_id"]
            for item in tenants.json()["items"]
        )

        subscription = client.get(
            f"/api/v1/subscriptions/{onboarding['tenant_public_id']}", headers=headers
        )
        assert subscription.status_code == 200, subscription.text
        assert subscription.json()["plan"]["slug"] == "free"
        assert subscription.json()["status"] == "active"

        refreshed = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert refreshed.status_code == 200, refreshed.text
        rotated = refreshed.json()
        assert rotated["refresh_token"] != tokens["refresh_token"]

        replay = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert replay.status_code == 401, replay.text
