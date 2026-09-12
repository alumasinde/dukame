from app.models.base import Base

# Import every module that defines a mapped class so SQLAlchemy's mapper
# registry is fully configured regardless of which entrypoint (API vs worker)
# imports this package first. Required even though the names below aren't
# used directly here — the import side effect is the point.
from app.modules.auth.models import identity, tokens  # noqa: F401
from app.modules.rbac.models import rbac  # noqa: F401
from app.modules.tenancy.models import tenant, business_type  # noqa: F401
from app.modules.subscriptions.models import subscription, billing  # noqa: F401
from app.modules.catalogue.models import (  # noqa: F401
    store,
    product,
    category,
    option,
    option_value,
    variant,
    variant_option_value,
    product_media,
)
from app.modules.commerce.models import (  # noqa: F401
    cart,
    cart_item,
    order,
    order_item,
    order_status,
    order_status_history,
    order_status_transition,
    order_delivery,
    order_notification,
    idempotency_key,
    inventory_movement,
    payment,
    payment_attempt,
    payment_event,
    payment_method,
    audit_log,
)
from app.modules.customers.models import customer  # noqa: F401

__all__ = ["Base"]