from pydantic import BaseModel, ConfigDict, Field, field_validator


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

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


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
