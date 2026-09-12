import pytest
from pydantic import ValidationError

from app.modules.catalogue.schemas.product import ProductCreate, ProductUpdate
from app.modules.catalogue.schemas.store import StoreCreate


def test_store_currency_is_normalized() -> None:
    payload = StoreCreate(name="Demo Store", slug="demo-store", status="active", currency="kes")
    assert payload.currency == "KES"


def test_product_rejects_invalid_compare_at_price() -> None:
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Phone",
            slug="phone",
            price_minor=10000,
            compare_at_price_minor=9000,
            currency="KES",
            status="active",
        )


def test_product_accepts_valid_compare_at_price() -> None:
    payload = ProductCreate(
        name="Phone",
        slug="phone",
        price_minor=9000,
        compare_at_price_minor=10000,
        currency="KES",
        status="active",
    )
    assert payload.compare_at_price_minor == 10000


@pytest.mark.parametrize("field", ["name", "slug", "price_minor", "currency", "inventory_tracking", "status"])
def test_product_update_rejects_null_for_required_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        ProductUpdate(**{field: None})


def test_product_update_allows_clearing_optional_fields() -> None:
    payload = ProductUpdate(description=None, sku=None, compare_at_price_minor=None, category_public_id=None)
    assert payload.model_dump(exclude_unset=True) == {
        "description": None,
        "sku": None,
        "compare_at_price_minor": None,
        "category_public_id": None,
    }
