from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_inventory_movement_model_is_registered() -> None:
    models = read("app/modules/commerce/models/__init__.py")
    env = read("migrations/env.py")
    assert "InventoryMovement" in models
    assert "InventoryMovement" in env


def test_inventory_migration_enforces_non_negative_stock() -> None:
    migration = read("migrations/versions/0020_inventory_ledger.py")
    assert "ck_products_inventory_quantity_nonnegative" in migration
    assert "ck_product_variants_inventory_quantity_nonnegative" in migration
    assert "quantity_before >= 0" in migration
    assert "quantity_after >= 0" in migration


def test_inventory_adjustment_is_atomic_and_locked() -> None:
    service = read("app/modules/commerce/inventory_service.py")
    assert "with_for_update()" in service
    assert "owner.inventory_quantity = after" in service
    assert "await self.db.commit()" in service
    assert "after < 0" in service


def test_catalogue_cannot_bypass_inventory_ledger() -> None:
    product_service = read("app/modules/catalogue/services/product.py")
    variant_service = read("app/modules/catalogue/services/variants.py")
    expected = "Inventory quantity must be changed through the inventory adjustment API"
    assert expected in product_service
    assert expected in variant_service


def test_inventory_adjustment_requires_granular_permission() -> None:
    migration = read("migrations/versions/0021_inventory_permissions.py")
    service = read("app/modules/commerce/inventory_service.py")
    route = read("app/modules/catalogue/routes/inventory.py")
    assert "inventory.adjust" in migration
    assert '"inventory.adjust"' in service
    assert "/adjust" in route
