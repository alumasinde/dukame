from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_delivery_storage_and_permissions_are_registered() -> None:
    models = read("app/modules/commerce/models/__init__.py")
    env = read("migrations/env.py")
    migration = read("migrations/versions/0024_delivery_permissions.py")
    assert "OrderDelivery" in models
    assert "OrderDelivery" in env
    assert "delivery.assign" in migration
    assert "delivery.otp.issue" in migration
    assert "delivery.confirm" in migration


def test_delivery_records_confirmation_actor_and_timestamp() -> None:
    model = read("app/modules/commerce/models/order_delivery.py")
    service = read("app/modules/commerce/delivery_service.py")
    assert "delivered_at" in model
    assert "delivered_by_user_id" in model
    assert "delivery_note" in model
    assert "delivery.status = \"delivered\"" in service
    assert "delivery.delivered_at = now" in service
    assert "delivery.delivered_by_user_id = user.id" in service


def test_delivery_requires_hashed_otp_and_attempt_limits() -> None:
    service = read("app/modules/commerce/delivery_service.py")
    config = read("app/core/config.py")
    assert "otp_hash" in service
    assert "compare_digest" in service
    assert "delivery_otp_max_attempts" in service
    assert "delivery_otp_ttl_minutes" in config


def test_delivery_assignee_is_tenant_scoped() -> None:
    service = read("app/modules/commerce/delivery_service.py")
    assert "TenantUser" in service
    assert "TenantUser.tenant_id == store.tenant_id" in service
    assert "TenantUser.status == \"active\"" in service


def test_delivery_api_is_exposed() -> None:
    routes = read("app/modules/commerce/routes/delivery.py")
    api = read("app/api/v1/router.py")
    assert "/otp" in routes
    assert "/confirm" in routes
    assert "delivery_router" in api
