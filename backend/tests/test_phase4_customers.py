"""Phase 4 customer management contract tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_customer_model_is_store_scoped() -> None:
    model = read("app/modules/customers/models/customer.py")
    migration = read("migrations/versions/0028_customers.py")
    assert 'store_id: Mapped[int]' in model
    assert 'UniqueConstraint("store_id", "phone"' in model
    assert 'customers' in migration
    assert '0027_audit_logs' in migration
    assert 'fk_orders_customer_id' in migration


def test_customer_api_has_search_and_lifecycle_permissions() -> None:
    routes = read("app/modules/customers/routes/customers.py")
    service = read("app/modules/customers/services/customer.py")
    permissions = read("migrations/versions/0029_customer_permissions.py")
    assert 'prefix="/tenants/{tenant_public_id}/customers"' in routes
    assert 'search: str | None' in routes
    assert 'customers.read' in service
    assert 'customers.manage' in service
    assert 'customers.read' in permissions
    assert 'customers.manage' in permissions


def test_customer_changes_are_audited() -> None:
    service = read("app/modules/customers/services/customer.py")
    assert 'action="customer.created"' in service
    assert 'action="customer.updated"' in service
    assert 'before=' in service
    assert 'after=' in service


def test_order_model_exposes_customer_relationship() -> None:
    order = read("app/modules/commerce/models/order.py")
    assert 'customer_id: Mapped[int | None]' in order
    assert 'customer: Mapped["Customer | None"]' in order
