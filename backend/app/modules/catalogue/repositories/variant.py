from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalogue.models.variant import ProductVariant
from app.modules.catalogue.models.variant_option_value import ProductVariantOptionValue


class VariantRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, product_id: int) -> list[ProductVariant]:
        result = await self.db.scalars(
            select(ProductVariant)
            .options(selectinload(ProductVariant.option_value_links).selectinload(ProductVariantOptionValue.option_value))
            .where(ProductVariant.product_id == product_id)
            .order_by(ProductVariant.created_at, ProductVariant.id)
        )
        return list(result.all())

    async def get(self, product_id: int, public_id: str) -> ProductVariant | None:
        return await self.db.scalar(
            select(ProductVariant)
            .options(selectinload(ProductVariant.option_value_links).selectinload(ProductVariantOptionValue.option_value))
            .where(ProductVariant.product_id == product_id, ProductVariant.public_id == public_id)
        )

    async def get_by_sku(self, store_id: int, sku: str) -> ProductVariant | None:
        return await self.db.scalar(select(ProductVariant).where(ProductVariant.store_id == store_id, ProductVariant.sku == sku))

    async def create(self, **values) -> ProductVariant:
        variant = ProductVariant(**values)
        self.db.add(variant)
        await self.db.flush()
        return variant

    async def delete(self, variant: ProductVariant) -> None:
        await self.db.delete(variant)
