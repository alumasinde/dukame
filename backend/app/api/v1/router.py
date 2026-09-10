from fastapi import APIRouter

from app.api.v1.routes import health
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(health.router)


@api_router.get("", tags=["system"])
async def api_root() -> dict[str, str]:
    return {"service": settings.app_name, "version": settings.app_version}
