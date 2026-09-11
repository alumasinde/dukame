from pydantic import ValidationError

from app.models.base import Base
from app.modules.catalogue.models import (
    ProductMedia,
    ProductOption,
    ProductOptionValue,
    ProductVariant,
    ProductVariantOptionValue,
)
from app.modules.catalogue.schemas.media import ProductMediaCreate
from app.modules.catalogue.schemas.option import OptionCreate
from app.modules.catalogue.schemas.variant import VariantCreate


def test_catalogue_models_are_registered() -> None:
    expected_tables = {
        "product_media",
        "product_options",
        "product_option_values",
        "product_variants",
        "product_variant_option_values",
    }
    assert expected_tables.issubset(Base.metadata.tables)
    assert ProductMedia.__tablename__ == "product_media"
    assert ProductOption.__tablename__ == "product_options"
    assert ProductOptionValue.__tablename__ == "product_option_values"
    assert ProductVariant.__tablename__ == "product_variants"
    assert ProductVariantOptionValue.__tablename__ == "product_variant_option_values"


def test_option_schema_requires_slug_safe_identifier() -> None:
    option = OptionCreate(name="Colour", slug="colour", status="active")
    assert option.slug == "colour"


def test_variant_schema_rejects_negative_inventory() -> None:
    try:
        VariantCreate(status="active", inventory_quantity=-1)
    except ValueError:
        return
    raise AssertionError("negative inventory should be rejected")


def test_media_schema_accepts_valid_image_url() -> None:
    media = ProductMediaCreate(url="https://cdn.example.com/products/phone.jpg")
    assert str(media.url) == "https://cdn.example.com/products/phone.jpg"
    assert media.media_type == "image"
    assert media.sort_order == 0


def test_media_schema_rejects_negative_sort_order() -> None:
    try:
        ProductMediaCreate(
            url="https://cdn.example.com/products/phone.jpg",
            sort_order=-1,
        )
    except ValidationError:
        return
    raise AssertionError("negative media sort order should be rejected")
