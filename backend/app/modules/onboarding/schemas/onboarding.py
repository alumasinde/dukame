from pydantic import BaseModel, Field


class OnboardingStatus(BaseModel):
    completed: bool
    current_step: str | None
    total_steps: int
    tenant_public_id: str | None = None


class CompleteOnboardingRequest(BaseModel):
    shop_name: str = Field(min_length=2, max_length=255)
    shop_slug: str | None = Field(default=None, min_length=3, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
