# app/modules/commerce/services/order_service.py
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models.identity import User
from app.modules.catalogue.models.store import Store
from app.modules.commerce.schemas import CheckoutRequest, OrderStatusUpdate
from app.modules.commerce.services.order_checkout_service import OrderCheckoutService
from app.modules.commerce.services.order_inventory_service import OrderInventoryService
from app.modules.commerce.services.order_query_service import OrderQueryService
from app.modules.commerce.services.order_status_service import OrderStatusService


class OrderService:
    """
    Facade service that combines order-related functionality.
    
    This maintains backward compatibility while delegating to specialized services.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.checkout = OrderCheckoutService(db)
        self.inventory = OrderInventoryService(db)
        self.status = OrderStatusService(db)
        self.query = OrderQueryService(db)

    # Checkout methods (delegated to OrderCheckoutService)
    async def checkout(
        self,
        store: Store,
        token: str,
        payload: CheckoutRequest,
        idempotency_key: str | None = None,
    ):
        """Create an order from a cart."""
        return await self.checkout.checkout(store, token, payload, idempotency_key)

    # Inventory methods (delegated to OrderInventoryService)
    async def finalize_order_payment(self, order_id: int) -> None:
        """Finalize order after payment confirmation."""
        return await self.inventory.finalize_order_payment(order_id)

    async def _release_order_reservations(self, order_id: int, reason: str = "payment_failed") -> None:
        """Release pending stock reservations."""
        return await self.inventory._release_order_reservations(order_id, reason)

    async def _restore_cancelled_order_inventory(self, order, store_id: int, actor_user_id: int) -> None:
        """Restore inventory for cancelled order."""
        return await self.inventory.restore_cancelled_order_inventory(order, store_id, actor_user_id)

    # Status methods (delegated to OrderStatusService)
    async def update_order_status(
        self,
        user: User,
        tenant_public_id: str,
        public_id: str,
        payload: OrderStatusUpdate,
        idempotency_key: str | None = None,
    ):
        """Update order status."""
        return await self.status.update_order_status(user, tenant_public_id, public_id, payload, idempotency_key)

    # Query methods (delegated to OrderQueryService)
    async def list_orders(
        self,
        user: User,
        tenant_public_id: str,
        offset: int,
        limit: int,
        status_public_id: str | None,
    ) -> list:
        """List orders."""
        return await self.query.list_orders(user, tenant_public_id, offset, limit, status_public_id)

    async def get_order(
        self,
        user: User,
        tenant_public_id: str,
        public_id: str,
    ):
        """Get a single order."""
        return await self.query.get_order(user, tenant_public_id, public_id)

    async def list_statuses(
        self,
        user: User,
        tenant_public_id: str,
    ) -> list:
        """List order statuses."""
        return await self.query.list_statuses(user, tenant_public_id)

    async def list_next_statuses(
        self,
        user: User,
        tenant_public_id: str,
        public_id: str,
    ) -> list:
        """List next statuses for an order."""
        return await self.query.list_next_statuses(user, tenant_public_id, public_id)

    async def get_public_order(
        self,
        store: Store,
        token: str,
    ):
        """Get public order by tracking token."""
        return await self.query.get_public_order(store, token)