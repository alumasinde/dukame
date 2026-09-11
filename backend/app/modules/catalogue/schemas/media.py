from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ProductMediaCreate(BaseModel):
    url: HttpUrl
    alt_text: str | None = Field(default=None, max_length=255)
    media_type: str = Field(default="image", min_length=1, max_length=32)
    sort_order: int = Field(default=0, ge=0)
    status: str = Field(default="active", min_length=1, max_length=32)


class ProductMediaUpdate(BaseModel):
    url: HttpUrl | None = None
    alt_text: str | None = Field(default=None, max_length=255)
    media_type: str | None = Field(default=None, min_length=1, max_length=32)
    sort_order: int | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, min_length=1, max_length=32)


class ProductMediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    url: str
    alt_text: str | None
    media_type: str
    sort_order: int
    status: str
