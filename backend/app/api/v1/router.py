from fastapi import APIRouter

from app.api.v1.routes import auth, health, members, roles, subscriptions, tenants
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(tenants.router)
api_router.include_router(subscriptions.router)
api_router.include_router(roles.router)
api_router.include_router(members.router)


@api_router.get("", tags=["system"])
async def api_root() -> dict[str, str]:
    return {"service": settings.app_name, "version": settings.app_version}
