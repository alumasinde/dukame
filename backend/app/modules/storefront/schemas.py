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
