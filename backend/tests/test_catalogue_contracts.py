import pytest
from pydantic import ValidationError

from app.modules.catalogue.schemas.category import CategoryUpdate
from app.modules.catalogue.schemas.option import OptionUpdate, OptionValueUpdate
from app.modules.catalogue.schemas.product import ProductCreate, ProductUpdate
from app.modules.catalogue.schemas.store import StoreCreate, StoreUpdate
from app.modules.catalogue.schemas.variant import VariantCreate, VariantUpdate


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


def test_product_create_normalizes_status_and_blank_sku() -> None:
    payload = ProductCreate(
        name="  Phone  ",
        slug="phone",
        price_minor=1000,
        currency="kes",
        status="ACTIVE",
        sku="   ",
        description="  ",
    )
    assert payload.name == "Phone"
    assert payload.currency == "KES"
    assert payload.status == "active"
    assert payload.sku is None
    assert payload.description is None


def test_product_create_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Phone",
            slug="phone",
            price_minor=1000,
            currency="KES",
            status="deleted",
        )


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


def test_product_update_rejects_empty_payload() -> None:
    with pytest.raises(ValidationError):
        ProductUpdate()


def test_product_update_normalizes_blank_sku_and_status() -> None:
    payload = ProductUpdate(sku="  ", status="Draft", name=" Updated Phone ")
    assert payload.sku is None
    assert payload.status == "draft"
    assert payload.name == "Updated Phone"


def test_product_update_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        ProductUpdate(status="removed")


def test_product_update_rejects_compare_below_price_when_both_set() -> None:
    with pytest.raises(ValidationError):
        ProductUpdate(price_minor=5000, compare_at_price_minor=4000)


@pytest.mark.parametrize(
    "schema,field",
    [
        (CategoryUpdate, "name"),
        (CategoryUpdate, "slug"),
        (CategoryUpdate, "status"),
        (StoreUpdate, "name"),
        (StoreUpdate, "currency"),
        (OptionUpdate, "name"),
        (OptionValueUpdate, "slug"),
        (VariantUpdate, "status"),
        (VariantUpdate, "inventory_tracking"),
    ],
)
def test_catalogue_updates_reject_null_for_required_fields(schema, field: str) -> None:
    with pytest.raises(ValidationError):
        schema(**{field: None})


def test_category_and_store_updates_reject_empty_payload() -> None:
    with pytest.raises(ValidationError):
        CategoryUpdate()
    with pytest.raises(ValidationError):
        StoreUpdate()
    with pytest.raises(ValidationError):
        OptionUpdate()
    with pytest.raises(ValidationError):
        VariantUpdate()


def test_variant_create_rejects_compare_below_price() -> None:
    with pytest.raises(ValidationError):
        VariantCreate(status="active", price_minor=1000, compare_at_price_minor=500)
