from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str | None = Field(default=None, max_length=2000)
    category_public_id: str | None = Field(default=None, min_length=8, max_length=64)
    sku: str | None = Field(default=None, max_length=100)
    price_minor: int = Field(ge=0)
    compare_at_price_minor: int | None = Field(default=None, ge=0)
    currency: str = Field(min_length=3, max_length=3)
    inventory_tracking: bool = True
    inventory_quantity: int = Field(default=0, ge=0)
    status: str = Field(min_length=1, max_length=32)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_compare_price(self):
        if self.compare_at_price_minor is not None and self.compare_at_price_minor < self.price_minor:
            raise ValueError("compare_at_price_minor must be greater than or equal to price_minor")
        return self


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    slug: str | None = Field(default=None, min_length=2, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str | None = Field(default=None, max_length=2000)
    category_public_id: str | None = Field(default=None, min_length=8, max_length=64)
    sku: str | None = Field(default=None, max_length=100)
    price_minor: int | None = Field(default=None, ge=0)
    compare_at_price_minor: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    inventory_tracking: bool | None = None
    inventory_quantity: int | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, min_length=1, max_length=32)

    @model_validator(mode="before")
    @classmethod
    def reject_null_required_fields(cls, value):
        if isinstance(value, dict):
            for field in ("name", "slug", "price_minor", "currency", "inventory_tracking", "status"):
                if field in value and value[field] is None:
                    raise ValueError(f"{field} cannot be null")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @model_validator(mode="after")
    def validate_compare_price(self):
        if self.price_minor is not None and self.compare_at_price_minor is not None and self.compare_at_price_minor < self.price_minor:
            raise ValueError("compare_at_price_minor must be greater than or equal to price_minor")
        return self


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    name: str
    slug: str
    description: str | None
    category_public_id: str | None = None
    sku: str | None
    price_minor: int
    compare_at_price_minor: int | None
    currency: str
    inventory_tracking: bool
    inventory_quantity: int
    status: str
