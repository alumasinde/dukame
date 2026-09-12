from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.modules.auth.models.identity import User
from app.modules.catalogue.models.store import Store
from app.modules.catalogue.services.context import resolve_store
from app.modules.commerce.audit_service import record_audit
from app.modules.commerce.models.order import Order
from app.modules.commerce.models.order_delivery import OrderDelivery
from app.modules.rbac.services.rbac import require_permission
from app.modules.tenancy.models.tenant import TenantUser


class DeliveryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create(self, user: User, tenant_public_id: str, order_public_id: str) -> OrderDelivery:
        store = await resolve_store(self.db, user, tenant_public_id, "orders.read")
        delivery = await self._delivery(store.id, order_public_id, lock=True)
        if delivery is None:
            delivery = await self._create_locked(store, order_public_id)
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
        before = {"status": delivery.status, "assigned_user_id": delivery.assigned_user_id}
        delivery.assigned_user_id = assigned_user_id
        delivery.status = "assigned"
        await record_audit(
            self.db,
            tenant_id=store.tenant_id,
            store_id=store.id,
            actor_user_id=user.id,
            action="delivery.assigned",
            entity_type="order_delivery",
            entity_public_id=delivery.public_id,
            before=before,
            after={"status": delivery.status, "assigned_user_id": assigned_user_id},
        )
        await self.db.commit()
        return delivery

    async def issue_otp(self, user: User, tenant_public_id: str, order_public_id: str) -> tuple[OrderDelivery, str]:
        """
        Issue a one-time passcode for delivery confirmation.
        
        Security:
        - Generate 6-digit cryptographically random code
        - Store SHA256 hash (never store plaintext OTP)
        - Set expiry window (configurable, typically 30 min)
        - Reset attempt counter
        - Only send to verified customer phone via SMS (not in rider app)
        """
        store = await resolve_store(self.db, user, tenant_public_id, "delivery.otp.issue")
        await require_permission(self.db, user, store.tenant_id, "delivery.otp.issue")
        delivery = await self._delivery(store.id, order_public_id, lock=True)
        if delivery is None:
            delivery = await self._create_locked(store, order_public_id)
        if delivery.status == "delivered":
            raise HTTPException(status_code=409, detail="Delivery is already completed")
        if delivery.assigned_user_id is None:
            raise HTTPException(status_code=409, detail="Assign a delivery person before issuing a delivery OTP")
        
        # Generate 6-digit OTP
        otp = f"{secrets.randbelow(1_000_000):06d}"
        now = datetime.now(UTC)
        
        # Store only hash, not plaintext
        delivery.otp_hash = self._hash_otp(delivery.public_id, otp)
        delivery.otp_expires_at = now + timedelta(minutes=settings.delivery_otp_ttl_minutes or 30)
        delivery.otp_verified_at = None
        delivery.otp_attempts = 0
        delivery.status = "out_for_delivery"
        
        await record_audit(
            self.db,
            tenant_id=store.tenant_id,
            store_id=store.id,
            actor_user_id=user.id,
            action="delivery.otp.issued",
            entity_type="order_delivery",
            entity_public_id=delivery.public_id,
            after={"status": delivery.status, "otp_expires_at": delivery.otp_expires_at.isoformat()},
        )
        await self.db.commit()
        
        # NOTE: OTP should be sent to customer's verified phone via SMS
        # NOT exposed in rider app, logs, or API responses
        return delivery, otp

    async def confirm(self, user: User, tenant_public_id: str, order_public_id: str, otp: str, note: str | None) -> OrderDelivery:
        """
        Confirm delivery with OTP verification.
        
        Security checks:
        - Verify OTP is not expired
        - Verify OTP attempt limit not exceeded
        - Compare with hash (constant-time comparison)
        - Only assigned rider can confirm
        - Atomically mark as delivered with timestamp
        
        On failure:
        - Increment attempt counter but don't mark as delivered
        - Return error without revealing whether OTP format is correct
        """
        store = await resolve_store(self.db, user, tenant_public_id, "delivery.confirm")
        await require_permission(self.db, user, store.tenant_id, "delivery.confirm")
        delivery = await self._delivery(store.id, order_public_id, lock=True)
        if delivery is None:
            raise HTTPException(status_code=404, detail="Delivery not found")
        if delivery.status == "delivered":
            raise HTTPException(status_code=409, detail="Delivery is already completed")
        
        # Only assigned rider can confirm
        if delivery.assigned_user_id is not None and delivery.assigned_user_id != user.id:
            raise HTTPException(status_code=403, detail="Only the assigned delivery person can confirm this delivery")
        
        now = datetime.now(UTC)
        
        # Check OTP exists and is not expired
        if delivery.otp_hash is None or delivery.otp_expires_at is None or delivery.otp_expires_at <= now:
            raise HTTPException(status_code=409, detail="Delivery OTP is missing or expired")
        
        # Check attempt limit
        if delivery.otp_attempts >= (settings.delivery_otp_max_attempts or 3):
            raise HTTPException(status_code=429, detail="Delivery OTP attempt limit exceeded")
        
        # Increment attempt counter
        delivery.otp_attempts += 1
        
        # Verify OTP with constant-time comparison (prevents timing attacks)
        if not secrets.compare_digest(delivery.otp_hash, self._hash_otp(delivery.public_id, otp.strip())):
            # Save attempt but don't mark as delivered
            await self.db.commit()
            raise HTTPException(status_code=422, detail="Invalid delivery OTP")
        
        # OTP valid: mark delivery as completed
        delivery.status = "delivered"
        delivery.delivered_at = now
        delivery.delivered_by_user_id = user.id
        delivery.delivery_note = note.strip() if note else None
        delivery.otp_verified_at = now
        
        await record_audit(
            self.db,
            tenant_id=store.tenant_id,
            store_id=store.id,
            actor_user_id=user.id,
            action="delivery.confirmed",
            entity_type="order_delivery",
            entity_public_id=delivery.public_id,
            before={"status": "out_for_delivery", "otp_attempts": delivery.otp_attempts - 1},
            after={"status": delivery.status, "delivered_at": now.isoformat(), "delivery_note": delivery.delivery_note},
        )
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
        """Hash OTP with delivery_id as salt to prevent OTP reuse across deliveries."""
        return hashlib.sha256(f"{delivery_public_id}:{otp}".encode()).hexdigest()
