from app.models.base import Base
from app.modules.catalogue.models import ProductOption, ProductOptionValue, ProductVariant, ProductVariantOptionValue
from app.modules.catalogue.schemas.option import OptionCreate
from app.modules.catalogue.schemas.variant import VariantCreate


def test_catalogue_models_are_registered() -> None:
    assert {"product_options", "product_option_values", "product_variants", "product_variant_option_values"}.issubset(Base.metadata.tables)
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
