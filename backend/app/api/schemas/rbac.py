from pydantic import BaseModel, Field


class TenantRoleResponse(BaseModel):
    public_id: str
    name: str
    slug: str
    is_system: bool
    permissions: list[str]


class CreateRoleRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str | None = Field(default=None, min_length=2, max_length=100)
    permissions: list[str] = Field(default_factory=list, max_length=100)


class UpdateRolePermissionsRequest(BaseModel):
    permissions: list[str] = Field(default_factory=list, max_length=100)


class PermissionResponse(BaseModel):
    key: str
    name: str


class MemberResponse(BaseModel):
    user_public_id: str
    email: str
    first_name: str
    last_name: str
    role: str
    status: str


class UpdateMemberRoleRequest(BaseModel):
    role_public_id: str = Field(min_length=8, max_length=64)
