from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StorefrontMedia(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    url: str
    alt_text: str | None


class StorefrontCategory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    name: str
    slug: str
    description: str | None = None
    parent_public_id: str | None = None


class StorefrontVariantOption(BaseModel):
    option_public_id: str
    option_name: str
    value_public_id: str
    value_name: str


class StorefrontVariant(BaseModel):
    public_id: str
    sku: str | None
    price_minor: int | None
    inventory_tracking: bool
    inventory_quantity: int
    options: list[StorefrontVariantOption] = Field(default_factory=list)


class StorefrontProduct(BaseModel):
    public_id: str
    name: str
    slug: str
    description: str | None
    price_minor: int
    compare_at_price_minor: int | None
    currency: str
    inventory_tracking: bool
    inventory_quantity: int
    created_at: datetime | None = None
    category: StorefrontCategory | None
    media: list[StorefrontMedia] = Field(default_factory=list)
    variants: list[StorefrontVariant] = Field(default_factory=list)


class StorefrontResponse(BaseModel):
    public_id: str
    name: str
    slug: str
    description: str | None
    contact_phone: str | None = None
    currency: str
    status: str = "active"
    categories: list[StorefrontCategory]
    products: list[StorefrontProduct]
    total_products: int = 0


class StorefrontProductResponse(StorefrontProduct):
    pass
