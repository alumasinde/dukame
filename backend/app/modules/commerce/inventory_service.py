from __future__ import annotations

import secrets

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models.identity import User
from app.modules.catalogue.models.product import Product
from app.modules.catalogue.models.variant import ProductVariant
from app.modules.catalogue.services.context import resolve_store
from app.modules.commerce.models.inventory_movement import InventoryMovement
from app.modules.rbac.services.rbac import require_permission


ALLOWED_MOVEMENT_TYPES = {"restock", "adjustment", "damage", "loss", "return", "sale"}


class InventoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def adjust(
        self,
        user: User,
        tenant_public_id: str,
        product_public_id: str,
        variant_public_id: str | None,
        delta: int,
        movement_type: str,
        reason: str | None,
    ) -> InventoryMovement:
        store = await resolve_store(self.db, user, tenant_public_id, "inventory.adjust")
        await require_permission(self.db, user, store.tenant_id, "inventory.adjust")
        movement_type = movement_type.strip().lower()
        if movement_type not in ALLOWED_MOVEMENT_TYPES:
            raise HTTPException(status_code=422, detail="Unsupported inventory movement type")
        if delta == 0:
            raise HTTPException(status_code=422, detail="Inventory adjustment cannot be zero")
        if movement_type == "restock" and delta < 0:
            raise HTTPException(status_code=422, detail="Restock quantity must increase stock")
        if movement_type in {"damage", "loss", "sale"} and delta > 0:
            raise HTTPException(status_code=422, detail=f"{movement_type} quantity must decrease stock")
        if movement_type in {"adjustment", "return"} and not reason:
            raise HTTPException(status_code=422, detail="A reason is required for this movement")
        product = await self.db.scalar(
            select(Product).where(Product.store_id == store.id, Product.public_id == product_public_id).with_for_update()
        )
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        owner: Product | ProductVariant = product
        variant = None
        if variant_public_id is not None:
            variant = await self.db.scalar(
                select(ProductVariant)
                .where(
                    ProductVariant.store_id == store.id,
                    ProductVariant.product_id == product.id,
                    ProductVariant.public_id == variant_public_id,
                )
                .with_for_update()
            )
            if variant is None:
                raise HTTPException(status_code=404, detail="Product variant not found")
            owner = variant
        if not owner.inventory_tracking:
            raise HTTPException(status_code=409, detail="Inventory tracking is disabled for this item")
        before = owner.inventory_quantity
        after = before + delta
        if after < 0:
            raise HTTPException(status_code=409, detail=f"Only {before} item(s) are available")
        owner.inventory_quantity = after
        movement = InventoryMovement(
            public_id=secrets.token_hex(16),
            store_id=store.id,
            product_id=product.id,
            variant_id=variant.id if variant else None,
            movement_type=movement_type,
            quantity=abs(delta),
            quantity_before=before,
            quantity_after=after,
            reason=reason.strip() if reason else None,
            actor_user_id=user.id,
        )
        self.db.add(movement)
        await self.db.commit()
        return movement
