from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models.identity import User
from app.modules.catalogue.models.option_value import ProductOptionValue
from app.modules.catalogue.models.product import Product
from app.modules.catalogue.models.variant_option_value import ProductVariantOptionValue
from app.modules.catalogue.repositories.variant import VariantRepository
from app.modules.catalogue.schemas.variant import VariantCreate, VariantUpdate
from app.modules.catalogue.services.context import resolve_store


class VariantService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.variants = VariantRepository(db)

    async def list(self, user: User, tenant_public_id: str, product_public_id: str):
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.read")
        product = await self._product(store.id, product_public_id)
        return await self.variants.list(product.id)

    async def create(self, user: User, tenant_public_id: str, product_public_id: str, payload: VariantCreate):
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.manage")
        product = await self._product(store.id, product_public_id)
        values = await self._validate_values(store.id, payload.option_value_public_ids)
        self._validate_prices(product, payload.price_minor, payload.compare_at_price_minor)
        await self._ensure_unique_combination(product.id, {value.id for value in values})
        if payload.sku and await self.variants.get_by_sku(store.id, payload.sku):
            raise HTTPException(status_code=409, detail="Variant SKU already exists")
        try:
            variant = await self.variants.create(public_id=uuid.uuid4().hex, store_id=store.id, product_id=product.id, **payload.model_dump(exclude={"option_value_public_ids"}))
            await self._replace_values(variant.id, payload.option_value_public_ids)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status_code=409, detail="Variant could not be created with the supplied values") from None
        return await self.variants.get(product.id, variant.public_id)

    async def update(self, user: User, tenant_public_id: str, product_public_id: str, public_id: str, payload: VariantUpdate):
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.manage")
        product = await self._product(store.id, product_public_id)
        variant = await self.variants.get(product.id, public_id)
        if variant is None:
            raise HTTPException(status_code=404, detail="Variant not found")
        values = payload.model_dump(exclude_unset=True)
        if "inventory_quantity" in values:
            raise HTTPException(status_code=409, detail="Inventory quantity must be changed through the inventory adjustment API")
        option_ids = values.pop("option_value_public_ids", None)
        if option_ids is not None:
            option_values = await self._validate_values(store.id, option_ids)
            await self._ensure_unique_combination(product.id, {value.id for value in option_values}, variant.id)
        if "sku" in values and values["sku"] and values["sku"] != variant.sku and await self.variants.get_by_sku(store.id, values["sku"]):
            raise HTTPException(status_code=409, detail="Variant SKU already exists")
        self._validate_prices(product, values.get("price_minor", variant.price_minor), values.get("compare_at_price_minor", variant.compare_at_price_minor))
        for key, value in values.items():
            setattr(variant, key, value)
        try:
            if option_ids is not None:
                await self._replace_values(variant.id, option_ids)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status_code=409, detail="Variant could not be updated with the supplied values") from None
        return await self.variants.get(product.id, variant.public_id)

    async def delete(self, user: User, tenant_public_id: str, product_public_id: str, public_id: str) -> None:
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.manage")
        product = await self._product(store.id, product_public_id)
        variant = await self.variants.get(product.id, public_id)
        if variant is None:
            raise HTTPException(status_code=404, detail="Variant not found")
        await self.variants.delete(variant)
        await self.db.commit()

    async def _product(self, store_id: int, public_id: str) -> Product:
        product = await self.db.scalar(select(Product).where(Product.store_id == store_id, Product.public_id == public_id))
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    async def _validate_values(self, store_id: int, public_ids: list[str]) -> list[ProductOptionValue]:
        if len(public_ids) != len(set(public_ids)):
            raise HTTPException(status_code=422, detail="A variant cannot use the same option value twice")
        if not public_ids:
            return []
        result = await self.db.scalars(select(ProductOptionValue).join(ProductOptionValue.option).where(ProductOptionValue.public_id.in_(public_ids), ProductOptionValue.option.has(store_id=store_id)))
        values = list(result.all())
        if len(values) != len(public_ids):
            raise HTTPException(status_code=422, detail="One or more option values were not found in this store")
        if len({value.option_id for value in values}) != len(values):
            raise HTTPException(status_code=422, detail="A variant can contain only one value for each option")
        return values

    async def _ensure_unique_combination(self, product_id: int, option_value_ids: set[int], exclude_variant_id: int | None = None) -> None:
        variants = await self.variants.list(product_id)
        for variant in variants:
            if exclude_variant_id and variant.id == exclude_variant_id:
                continue
            existing = {link.option_value_id for link in variant.option_value_links}
            if existing == option_value_ids:
                raise HTTPException(status_code=409, detail="A variant with this option combination already exists")

    async def _replace_values(self, variant_id: int, public_ids: list[str]) -> None:
        await self.db.execute(delete(ProductVariantOptionValue).where(ProductVariantOptionValue.variant_id == variant_id))
        if public_ids:
            result = await self.db.scalars(select(ProductOptionValue).where(ProductOptionValue.public_id.in_(public_ids)))
            self.db.add_all([ProductVariantOptionValue(variant_id=variant_id, option_value_id=value.id) for value in result.all()])

    @staticmethod
    def _validate_prices(product: Product, price_minor: int | None, compare_at_price_minor: int | None) -> None:
        price = product.price_minor if price_minor is None else price_minor
        if compare_at_price_minor is not None and compare_at_price_minor < price:
            raise HTTPException(status_code=422, detail="compare_at_price_minor must be greater than or equal to price_minor")
