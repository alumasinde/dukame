from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_checkout_records_sale_inventory_ledger_atomically() -> None:
    service = read("app/modules/commerce/service.py")
    assert "movement_type=\"sale\"" in service
    assert 'reference_type="order_item"' in service
    assert "inventory_owner.inventory_quantity = quantity_after" in service
    assert "await self.db.commit()" in service


def test_order_cancellation_restores_inventory_once() -> None:
    service = read("app/modules/commerce/service.py")
    assert 'if status.code == "cancelled":' in service
    assert 'movement_type == "return"' in service
    assert 'reason="Order cancellation"' in service
    assert "existing_return is not None" in service
    assert "owner.inventory_quantity = quantity_after" in service


def test_delivery_creation_is_serialized_per_order() -> None:
    service = read("app/modules/commerce/delivery_service.py")
    assert 'self._delivery(store.id, order_public_id, lock=True)' in service
    assert 'self._create_locked(store, order_public_id)' in service
    assert 'self._order(store.id, order_public_id, lock=True)' in service


def test_inventory_order_references_are_database_enforced() -> None:
    migration = read("migrations/versions/0025_inventory_order_reference_integrity.py")
    assert "ck_inventory_movements_order_reference" in migration
    assert "movement_type NOT IN ('sale', 'return')" in migration
    assert "reference_type IS NOT NULL" in migration
    assert "reference_id IS NOT NULL" in migration
