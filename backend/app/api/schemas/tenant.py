from pydantic import BaseModel, Field


class CreateTenantRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str | None = Field(default=None, min_length=3, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class TenantResponse(BaseModel):
    public_id: str
    name: str
    slug: str
    status: str
    role: str


class TenantListResponse(BaseModel):
    items: list[TenantResponse]
