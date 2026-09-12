from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.modules.catalogue.schemas.common import reject_null_fields, validate_catalogue_status


class ProductMediaCreate(BaseModel):
    url: HttpUrl
    alt_text: str | None = Field(default=None, max_length=255)
    media_type: str = Field(default="image", min_length=1, max_length=32)
    sort_order: int = Field(default=0, ge=0)
    status: str = Field(default="active", min_length=1, max_length=32)

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        result = validate_catalogue_status(value)
        assert result is not None
        return result


class ProductMediaUpdate(BaseModel):
    url: HttpUrl | None = None
    alt_text: str | None = Field(default=None, max_length=255)
    media_type: str | None = Field(default=None, min_length=1, max_length=32)
    sort_order: int | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, min_length=1, max_length=32)

    @model_validator(mode="before")
    @classmethod
    def reject_null_required_fields(cls, value):
        return reject_null_fields(value, ("url", "media_type", "sort_order", "status"))

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str | None) -> str | None:
        return validate_catalogue_status(value)

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if self.model_fields_set == set():
            raise ValueError("at least one field must be provided for update")
        return self


class ProductMediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    url: str
    alt_text: str | None
    media_type: str
    sort_order: int
    status: str
