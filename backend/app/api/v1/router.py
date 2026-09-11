from fastapi import APIRouter

from app.api.v1.routes.health import router as health_router
from app.core.config import settings
from app.modules.auth.routes.auth import router as auth_router
from app.modules.catalogue.routes import categories_router, media_router, options_router, products_router, store_router, variants_router
from app.modules.onboarding.routes.onboarding import router as onboarding_router
from app.modules.rbac.routes.members import router as members_router
from app.modules.rbac.routes.roles import router as roles_router
from app.modules.storefront.routes import router as storefront_router
from app.modules.subscriptions.routes.subscriptions import router as subscriptions_router
from app.modules.tenancy.routes.tenants import router as tenants_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(onboarding_router)
api_router.include_router(tenants_router)
api_router.include_router(subscriptions_router)
api_router.include_router(roles_router)
api_router.include_router(members_router)
api_router.include_router(storefront_router)
api_router.include_router(store_router)
api_router.include_router(categories_router)
api_router.include_router(products_router)
api_router.include_router(options_router)
api_router.include_router(variants_router)
api_router.include_router(media_router)


@api_router.get("", tags=["system"])
async def api_root() -> dict[str, str]:
    return {"service": settings.app_name, "version": settings.app_version}
