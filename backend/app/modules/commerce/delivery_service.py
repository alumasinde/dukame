from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.auth.models.identity import User
from app.modules.catalogue.models.store import Store
from app.modules.catalogue.services.context import resolve_store
from app.modules.commerce.models.order import Order
from app.modules.commerce.models.order_delivery import OrderDelivery
from app.modules.rbac.services.rbac import require_permission
from app.modules.tenancy.models.tenant import TenantUser


class DeliveryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create(self, user: User, tenant_public_id: str, order_public_id: str) -> OrderDelivery:
        store = await resolve_store(self.db, user, tenant_public_id, "orders.read")
        order = await self._order(store.id, order_public_id, lock=False)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        delivery = await self.db.scalar(select(OrderDelivery).where(OrderDelivery.order_id == order.id))
        if delivery is None:
            delivery = OrderDelivery(public_id=secrets.token_hex(16), store_id=store.id, order_id=order.id, status="pending")
            self.db.add(delivery)
            await self.db.commit()
            await self.db.refresh(delivery)
        return delivery

    async def assign(self, user: User, tenant_public_id: str, order_public_id: str, assigned_user_id: int) -> OrderDelivery:
        store = await resolve_store(self.db, user, tenant_public_id, "delivery.assign")
        await require_permission(self.db, user, store.tenant_id, "delivery.assign")
        member = await self.db.scalar(select(TenantUser).where(TenantUser.tenant_id == store.tenant_id, TenantUser.user_id == assigned_user_id, TenantUser.status == "active"))
        if member is None:
            raise HTTPException(status_code=422, detail="Delivery person is not an active member of this business")
        delivery = await self._delivery(store.id, order_public_id, lock=True)
        if delivery is None:
            delivery = await self._create_locked(store, order_public_id)
        if delivery.status == "delivered":
            raise HTTPException(status_code=409, detail="Delivered orders cannot be reassigned")
        delivery.assigned_user_id = assigned_user_id
        delivery.status = "assigned"
        await self.db.commit()
        return delivery

    async def issue_otp(self, user: User, tenant_public_id: str, order_public_id: str) -> tuple[OrderDelivery, str]:
        store = await resolve_store(self.db, user, tenant_public_id, "delivery.otp.issue")
        await require_permission(self.db, user, store.tenant_id, "delivery.otp.issue")
        delivery = await self._delivery(store.id, order_public_id, lock=True)
        if delivery is None:
            delivery = await self._create_locked(store, order_public_id)
        if delivery.status == "delivered":
            raise HTTPException(status_code=409, detail="Delivery is already completed")
        if delivery.assigned_user_id is None:
            raise HTTPException(status_code=409, detail="Assign a delivery person before issuing a delivery OTP")
        otp = f"{secrets.randbelow(1_000_000):06d}"
        now = datetime.now(UTC)
        delivery.otp_hash = self._hash_otp(delivery.public_id, otp)
        delivery.otp_expires_at = now + timedelta(minutes=settings.delivery_otp_ttl_minutes)
        delivery.otp_verified_at = None
        delivery.otp_attempts = 0
        delivery.status = "out_for_delivery"
        await self.db.commit()
        return delivery, otp

    async def confirm(self, user: User, tenant_public_id: str, order_public_id: str, otp: str, note: str | None) -> OrderDelivery:
        store = await resolve_store(self.db, user, tenant_public_id, "delivery.confirm")
        await require_permission(self.db, user, store.tenant_id, "delivery.confirm")
        delivery = await self._delivery(store.id, order_public_id, lock=True)
        if delivery is None:
            raise HTTPException(status_code=404, detail="Delivery not found")
        if delivery.status == "delivered":
            raise HTTPException(status_code=409, detail="Delivery is already completed")
        if delivery.assigned_user_id is not None and delivery.assigned_user_id != user.id:
            raise HTTPException(status_code=403, detail="Only the assigned delivery person can confirm this delivery")
        now = datetime.now(UTC)
        if delivery.otp_hash is None or delivery.otp_expires_at is None or delivery.otp_expires_at <= now:
            raise HTTPException(status_code=409, detail="Delivery OTP is missing or expired")
        if delivery.otp_attempts >= settings.delivery_otp_max_attempts:
            raise HTTPException(status_code=429, detail="Delivery OTP attempt limit exceeded")
        delivery.otp_attempts += 1
        if not secrets.compare_digest(delivery.otp_hash, self._hash_otp(delivery.public_id, otp.strip())):
            await self.db.commit()
            raise HTTPException(status_code=422, detail="Invalid delivery OTP")
        delivery.status = "delivered"
        delivery.delivered_at = now
        delivery.delivered_by_user_id = user.id
        delivery.delivery_note = note.strip() if note else None
        delivery.otp_verified_at = now
        await self.db.commit()
        return delivery

    async def _create_locked(self, store: Store, order_public_id: str) -> OrderDelivery:
        order = await self._order(store.id, order_public_id, lock=True)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        delivery = await self.db.scalar(select(OrderDelivery).where(OrderDelivery.order_id == order.id).with_for_update())
        if delivery is None:
            delivery = OrderDelivery(public_id=secrets.token_hex(16), store_id=store.id, order_id=order.id, status="pending")
            self.db.add(delivery)
            await self.db.flush()
        return delivery

    async def _delivery(self, store_id: int, order_public_id: str, lock: bool) -> OrderDelivery | None:
        stmt = select(OrderDelivery).join(Order).where(OrderDelivery.store_id == store_id, Order.public_id == order_public_id)
        if lock:
            stmt = stmt.with_for_update()
        return await self.db.scalar(stmt)

    async def _order(self, store_id: int, public_id: str, lock: bool) -> Order | None:
        stmt = select(Order).where(Order.store_id == store_id, Order.public_id == public_id)
        if lock:
            stmt = stmt.with_for_update()
        return await self.db.scalar(stmt)

    @staticmethod
    def _hash_otp(delivery_public_id: str, otp: str) -> str:
        return hashlib.sha256(f"{delivery_public_id}:{otp}".encode()).hexdigest()
