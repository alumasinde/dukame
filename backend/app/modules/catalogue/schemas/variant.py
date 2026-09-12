from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.catalogue.schemas.common import (
    normalize_optional_blank_str,
    reject_null_fields,
    validate_catalogue_status,
)


class VariantCreate(BaseModel):
    sku: str | None = Field(default=None, max_length=100)
    price_minor: int | None = Field(default=None, ge=0)
    compare_at_price_minor: int | None = Field(default=None, ge=0)
    inventory_tracking: bool = True
    inventory_quantity: int = Field(default=0, ge=0)
    status: str = Field(min_length=1, max_length=32)
    option_value_public_ids: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str | None) -> str | None:
        return normalize_optional_blank_str(value)

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        result = validate_catalogue_status(value)
        assert result is not None
        return result

    @model_validator(mode="after")
    def validate_compare_price(self):
        if (
            self.price_minor is not None
            and self.compare_at_price_minor is not None
            and self.compare_at_price_minor < self.price_minor
        ):
            raise ValueError("compare_at_price_minor must be greater than or equal to price_minor")
        return self


class VariantUpdate(BaseModel):
    sku: str | None = Field(default=None, max_length=100)
    price_minor: int | None = Field(default=None, ge=0)
    compare_at_price_minor: int | None = Field(default=None, ge=0)
    inventory_tracking: bool | None = None
    inventory_quantity: int | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, min_length=1, max_length=32)
    option_value_public_ids: list[str] | None = Field(default=None, max_length=50)

    @model_validator(mode="before")
    @classmethod
    def reject_null_required_fields(cls, value):
        return reject_null_fields(value, ("inventory_tracking", "status"))

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str | None) -> str | None:
        return normalize_optional_blank_str(value)

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str | None) -> str | None:
        return validate_catalogue_status(value)

    @model_validator(mode="after")
    def validate_compare_price_and_non_empty(self):
        if self.model_fields_set == set():
            raise ValueError("at least one field must be provided for update")
        if (
            self.price_minor is not None
            and self.compare_at_price_minor is not None
            and self.compare_at_price_minor < self.price_minor
        ):
            raise ValueError("compare_at_price_minor must be greater than or equal to price_minor")
        return self


class VariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    sku: str | None
    price_minor: int | None
    compare_at_price_minor: int | None
    inventory_tracking: bool
    inventory_quantity: int
    status: str
    option_value_public_ids: list[str]
