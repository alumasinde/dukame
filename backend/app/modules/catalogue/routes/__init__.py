from app.modules.catalogue.routes.categories import router as categories_router
from app.modules.catalogue.routes.products import router as products_router
from app.modules.catalogue.routes.store import router as store_router

__all__ = ["store_router", "categories_router", "products_router"]
