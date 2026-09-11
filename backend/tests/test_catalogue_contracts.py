import pytest
from pydantic import ValidationError

from app.modules.catalogue.schemas.product import ProductCreate
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
