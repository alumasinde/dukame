from pydantic import BaseModel, ConfigDict, Field


class VariantCreate(BaseModel):
    sku: str | None = Field(default=None, max_length=100)
    price_minor: int | None = Field(default=None, ge=0)
    compare_at_price_minor: int | None = Field(default=None, ge=0)
    inventory_tracking: bool = True
    inventory_quantity: int = Field(default=0, ge=0)
    status: str = Field(min_length=1, max_length=32)
    option_value_public_ids: list[str] = Field(default_factory=list, max_length=50)


class VariantUpdate(BaseModel):
    sku: str | None = Field(default=None, max_length=100)
    price_minor: int | None = Field(default=None, ge=0)
    compare_at_price_minor: int | None = Field(default=None, ge=0)
    inventory_tracking: bool | None = None
    inventory_quantity: int | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, min_length=1, max_length=32)
    option_value_public_ids: list[str] | None = Field(default=None, max_length=50)


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
