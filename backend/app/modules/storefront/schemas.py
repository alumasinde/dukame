from pydantic import BaseModel, ConfigDict


class StorefrontMedia(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    url: str
    alt_text: str | None


class StorefrontCategory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    name: str
    slug: str
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
    options: list[StorefrontVariantOption]


class StorefrontProduct(BaseModel):
    public_id: str
    name: str
    slug: str
    description: str | None
    price_minor: int
    compare_at_price_minor: int | None
    currency: str
    category: StorefrontCategory | None
    media: list[StorefrontMedia]
    variants: list[StorefrontVariant] = []


class StorefrontResponse(BaseModel):
    public_id: str
    name: str
    slug: str
    description: str | None
    currency: str
    categories: list[StorefrontCategory]
    products: list[StorefrontProduct]


class StorefrontProductResponse(StorefrontProduct):
    pass
