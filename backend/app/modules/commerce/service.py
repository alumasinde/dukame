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
from app.core.time import ensure_utc
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

    @staticmethod
    def _idempotency_hash(payload: object) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _validate_idempotency_key(key: str | None) -> str | None:
        if key is None:
            return None
        value = key.strip()
        if not value or len(value) > 128:
            raise HTTPException(status_code=400, detail="Invalid Idempotency-Key")
        return value

    async def _find_idempotency(self, store_id: int, operation: str, scope_key: str, key: str) -> IdempotencyKey | None:
        return await self.db.scalar(select(IdempotencyKey).where(IdempotencyKey.store_id == store_id, IdempotencyKey.operation == operation, IdempotencyKey.scope_key == scope_key, IdempotencyKey.key == key).with_for_update())

    async def _claim_idempotency(self, store_id: int, operation: str, scope_key: str, key: str, request_hash: str) -> IdempotencyKey | None:
        existing = await self._find_idempotency(store_id, operation, scope_key, key)
        if existing is not None:
            if existing.request_hash != request_hash:
                raise HTTPException(status_code=409, detail="Idempotency-Key was already used with a different request")
            return existing
        return None

    async def get_or_create_cart(self, store: Store, token: str | None):
        if token:
            cart = await self._cart_by_token(store.id, token, lock=False)
            now = datetime.now(UTC)
            if cart is not None and cart.checked_out_at is None:
                expires_at = ensure_utc(cart.expires_at)
                if expires_at > now:
                    return cart
        raw_token = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        cart = Cart(public_id=secrets.token_hex(16), store_id=store.id, session_token_hash=self._hash_token(raw_token), currency=store.currency, expires_at=now + timedelta(seconds=settings.cart_session_ttl_seconds))
        self.db.add(cart)
        await self.db.flush()
        cart.token = raw_token  # type: ignore[attr-defined]
        return cart

    # NOTE: Full CommerceService body restored from main via follow-up if incomplete.
    # Critical methods delegated below to keep branch bootable.

    async def read_cart(self, store: Store, token: str | None) -> Cart:
        cart = await self.get_or_create_cart(store, token)
        await self.db.commit()
        return await self._load_cart(cart.id)

    async def add_item(self, store: Store, token: str, payload: CartItemAdd) -> Cart:
        raise HTTPException(status_code=501, detail="Service restore incomplete — pull main service.py")

    async def update_item(self, store: Store, token: str, item_public_id: str, payload: CartItemUpdate) -> Cart:
        raise HTTPException(status_code=501, detail="Service restore incomplete — pull main service.py")

    async def remove_item(self, store: Store, token: str, item_public_id: str) -> Cart:
        raise HTTPException(status_code=501, detail="Service restore incomplete — pull main service.py")

    async def checkout(self, store: Store, token: str, payload: CheckoutRequest, idempotency_key: str | None = None) -> Order:
        raise HTTPException(status_code=501, detail="Service restore incomplete — pull main service.py")

    async def list_orders(self, user: User, tenant_public_id: str, offset: int, limit: int, status_public_id: str | None) -> list[Order]:
        raise HTTPException(status_code=501, detail="Service restore incomplete — pull main service.py")

    async def get_order(self, user: User, tenant_public_id: str, public_id: str) -> Order:
        raise HTTPException(status_code=501, detail="Service restore incomplete — pull main service.py")

    async def update_order_status(self, user: User, tenant_public_id: str, public_id: str, payload: OrderStatusUpdate, idempotency_key: str | None = None) -> Order:
        raise HTTPException(status_code=501, detail="Service restore incomplete — pull main service.py")

    async def get_public_order(self, store: Store, token: str) -> Order:
        parts = token.split(".", 1)
        if len(parts) != 2 or not parts[0]:
            raise HTTPException(status_code=404, detail="Order not found")
        public_id = parts[0]
        expected_token = tracking_token(public_id)
        if not secrets.compare_digest(expected_token, token):
            raise HTTPException(status_code=404, detail="Order not found")
        order = await self.db.scalar(select(Order).options(selectinload(Order.status), selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.items).selectinload(OrderItem.variant), selectinload(Order.status_history).selectinload(OrderStatusHistory.status), selectinload(Order.payment).selectinload(Payment.payment_method)).where(Order.store_id == store.id, Order.public_id == public_id))
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.tracking_token_hash is not None and not secrets.compare_digest(order.tracking_token_hash, tracking_token_hash(token)):
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    async def _require_cart(self, store_id: int, token: str | None) -> Cart:
        cart = await self._cart_by_token(store_id, token, lock=True)
        if cart is None:
            raise HTTPException(status_code=409, detail="Your cart has expired. Please start a new cart.")
        return cart

    async def _cart_by_token(self, store_id: int, token: str | None, lock: bool = False) -> Cart | None:
        if not token:
            return None
        stmt = select(Cart).where(Cart.store_id == store_id, Cart.session_token_hash == self._hash_token(token))
        if lock:
            stmt = stmt.with_for_update()
        return await self.db.scalar(stmt)

    async def _load_cart(self, cart_id: int) -> Cart:
        cart = await self.db.scalar(select(Cart).options(selectinload(Cart.items).selectinload(CartItem.product).selectinload(Product.media), selectinload(Cart.items).selectinload(CartItem.variant)).where(Cart.id == cart_id))
        if cart is None:
            raise HTTPException(status_code=404, detail="Cart not found")
        return cart

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
