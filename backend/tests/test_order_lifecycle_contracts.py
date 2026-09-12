import importlib
import inspect

from app.modules.commerce.models.idempotency_key import IdempotencyKey
from app.modules.commerce.models.order_status_transition import OrderStatusTransition
from app.modules.commerce.service import CommerceService

transition_permissions = importlib.import_module(
    "migrations.versions.0018_order_transition_permissions"
)


def test_order_transition_requires_a_permission() -> None:
    column = OrderStatusTransition.__table__.c.permission_id
    assert column.nullable is False
    assert column.foreign_keys


def test_every_seeded_order_transition_has_a_granular_permission() -> None:
    seeded = {
        ("pending", "confirmed"),
        ("pending", "cancelled"),
        ("confirmed", "processing"),
        ("confirmed", "cancelled"),
        ("processing", "ready"),
        ("processing", "cancelled"),
        ("ready", "completed"),
    }
    assert set(transition_permissions.TRANSITION_PERMISSIONS) == seeded
    assert all(
        value.startswith("orders.") and value != "orders.status.manage"
        for value in transition_permissions.TRANSITION_PERMISSIONS.values()
    )


def test_status_update_no_longer_uses_broad_status_permission() -> None:
    source = inspect.getsource(CommerceService.update_order_status)
    assert '"orders.status.manage"' not in source
    assert "transition.permission.key" in source


def test_idempotency_key_is_store_and_operation_scoped() -> None:
    constraints = IdempotencyKey.__table__.constraints
    assert any(
        constraint.name == "uq_idempotency_store_operation_scope_key"
        and {column.name for column in constraint.columns}
        == {"store_id", "operation", "scope_key", "key"}
        for constraint in constraints
    )


def test_checkout_and_status_update_accept_idempotency_keys() -> None:
    assert "idempotency_key" in inspect.signature(CommerceService.checkout).parameters
    assert "idempotency_key" in inspect.signature(CommerceService.update_order_status).parameters
    assert "_claim_idempotency" in inspect.getsource(CommerceService)
