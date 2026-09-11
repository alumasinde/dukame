from pydantic import BaseModel, Field


class CreateTenantRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str | None = Field(default=None, min_length=3, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    business_type_public_id: str | None = Field(default=None, min_length=1, max_length=32)


class TenantResponse(BaseModel):
    public_id: str
    name: str
    slug: str
    status: str
    role: str
    business_type_public_id: str | None = None
    business_type_name: str | None = None


class TenantListResponse(BaseModel):
    items: list[TenantResponse]
