from app.modules.catalogue.routes.categories import router as categories_router
from app.modules.catalogue.routes.media import router as media_router
from app.modules.catalogue.routes.options import router as options_router
from app.modules.catalogue.routes.products import router as products_router
from app.modules.catalogue.routes.store import router as store_router
from app.modules.catalogue.routes.variants import router as variants_router

__all__ = ["store_router", "categories_router", "products_router", "options_router", "variants_router", "media_router"]
