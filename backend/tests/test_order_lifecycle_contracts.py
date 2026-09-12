from app.modules.commerce.models.order_status_transition import OrderStatusTransition
from app.modules.commerce.service import CommerceService
from migrations.versions import _0018_order_transition_permissions as transition_permissions


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
    import inspect

    source = inspect.getsource(CommerceService.update_order_status)
    assert '"orders.status.manage"' not in source
    assert "transition.permission.key" in source
