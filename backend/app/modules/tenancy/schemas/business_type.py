from pydantic import BaseModel, ConfigDict


class BusinessTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    name: str
    slug: str
    description: str | None
    icon: str | None


class BusinessTypeListResponse(BaseModel):
    items: list[BusinessTypeResponse]
