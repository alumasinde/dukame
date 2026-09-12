from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.catalogue.schemas.common import reject_null_fields, validate_catalogue_status


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str | None = Field(default=None, max_length=1000)
    parent_public_id: str | None = Field(default=None, min_length=8, max_length=64)
    status: str = Field(min_length=1, max_length=32)
    sort_order: int = Field(default=0, ge=0)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        result = validate_catalogue_status(value)
        assert result is not None
        return result


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    slug: str | None = Field(default=None, min_length=2, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str | None = Field(default=None, max_length=1000)
    parent_public_id: str | None = Field(default=None, min_length=8, max_length=64)
    status: str | None = Field(default=None, min_length=1, max_length=32)
    sort_order: int | None = Field(default=None, ge=0)

    @model_validator(mode="before")
    @classmethod
    def reject_null_required_fields(cls, value):
        return reject_null_fields(value, ("name", "slug", "status", "sort_order"))

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str | None) -> str | None:
        return validate_catalogue_status(value)

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if self.model_fields_set == set():
            raise ValueError("at least one field must be provided for update")
        return self


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    name: str
    slug: str
    description: str | None
    parent_public_id: str | None = None
    status: str
    sort_order: int
