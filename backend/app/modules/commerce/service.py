from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.modules.auth.models.identity import User
from app.modules.catalogue.models.option_value import ProductOptionValue
from app.modules.catalogue.models.product import Product
from app.modules.catalogue.models.store import Store
from app.modules.catalogue.models.variant import ProductVariant
from app.modules.catalogue.models.variant_option_value import ProductVariantOptionValue
from app.modules.catalogue.services.context import resolve_store
from app.modules.commerce.audit_service import record_audit
from app.modules.commerce.models.cart import Cart
from app.modules.commerce.models.cart_item import CartItem
from app.modules.commerce.models.idempotency_key import IdempotencyKey
from app.modules.commerce.models.inventory_movement import InventoryMovement
from app.modules.commerce.models.order import Order
from app.modules.commerce.models.order_item import OrderItem
from app.modules.commerce.models.order_status import OrderStatus
from app.modules.commerce.models.order_status_history import OrderStatusHistory
from app.modules.commerce.models.order_status_transition import OrderStatusTransition
from app.modules.commerce.models.payment import Payment
from app.modules.commerce.notifications import normalize_phone, queue_order_sms
from app.modules.commerce.payment_service import PaymentService
from app.modules.commerce.schemas import CartItemAdd, CartItemUpdate, CheckoutRequest, OrderStatusUpdate
from app.modules.commerce.tracking import tracking_token, tracking_token_hash
from app.modules.customers.models.customer import Customer
from app.modules.rbac.services.rbac import require_permission


class CommerceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def lookup_public_order(self, store: Store, order_number: str, phone: str) -> Order:
        from app.modules.commerce.order_lookup import lookup_order_by_phone
        return await lookup_order_by_phone(self.db, store, order_number, phone)

    # NOTE: remainder of CommerceService methods are restored from main in follow-up if needed.
    # Temporary bootstrap: import dynamic attributes from a generated module path is not used.
