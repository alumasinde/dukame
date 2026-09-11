from pydantic import BaseModel, ConfigDict, Field


class OptionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    status: str = Field(min_length=1, max_length=32)
    sort_order: int = Field(default=0, ge=0)


class OptionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, min_length=1, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    status: str | None = Field(default=None, min_length=1, max_length=32)
    sort_order: int | None = Field(default=None, ge=0)


class OptionValueCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    status: str = Field(min_length=1, max_length=32)
    sort_order: int = Field(default=0, ge=0)


class OptionValueUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, min_length=1, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    status: str | None = Field(default=None, min_length=1, max_length=32)
    sort_order: int | None = Field(default=None, ge=0)


class OptionValueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    name: str
    slug: str
    status: str
    sort_order: int


class OptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    name: str
    slug: str
    status: str
    sort_order: int
    values: list[OptionValueResponse]
