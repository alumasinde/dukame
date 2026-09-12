from app.models.base import Base

def load_models() -> None:
    """Register every mapped class after base-model imports have completed.

    Importing models here at module-import time creates a circular dependency:
    a model imports ``app.models.base``, which initializes this package, which
    then imports that same model before its class definitions exist. Entrypoints
    call this function only once their initial imports are complete.
    """
    from app.modules.auth.models import identity, tokens  # noqa: F401
    from app.modules.rbac.models import rbac  # noqa: F401
    from app.modules.tenancy.models import business_type, tenant  # noqa: F401
    from app.modules.subscriptions.models import billing, subscription  # noqa: F401
    from app.modules.catalogue.models import (  # noqa: F401
        category,
        option,
        option_value,
        product,
        product_media,
        store,
        variant,
        variant_option_value,
    )
    from app.modules.commerce.models import (  # noqa: F401
        audit_log,
        cart,
        cart_item,
        idempotency_key,
        inventory_movement,
        order,
        order_delivery,
        order_item,
        order_notification,
        order_status,
        order_status_history,
        order_status_transition,
        payment,
        payment_attempt,
        payment_event,
        payment_method,
    )
    from app.modules.customers.models import customer  # noqa: F401


__all__ = ["Base", "load_models"]
