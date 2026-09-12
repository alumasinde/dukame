from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=7, max_length=32)
    email: EmailStr | None = None
    notes: str | None = Field(default=None, max_length=5000)


class CustomerUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, min_length=7, max_length=32)
    email: EmailStr | None = None
    notes: str | None = Field(default=None, max_length=5000)
    is_active: bool | None = None


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    first_name: str
    last_name: str
    phone: str
    email: EmailStr | None
    notes: str | None
    is_active: bool
    order_count: int = 0
