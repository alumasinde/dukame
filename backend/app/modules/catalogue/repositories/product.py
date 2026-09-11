from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalogue.models.product import Product


class ProductRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, store_id: int, offset: int, limit: int) -> list[Product]:
        result = await self.db.scalars(
            select(Product)
            .options(selectinload(Product.category))
            .where(Product.store_id == store_id)
            .order_by(Product.created_at.desc(), Product.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.all())

    async def get(self, store_id: int, public_id: str) -> Product | None:
        return await self.db.scalar(
            select(Product).options(selectinload(Product.category)).where(Product.store_id == store_id, Product.public_id == public_id)
        )

    async def get_by_slug(self, store_id: int, slug: str) -> Product | None:
        return await self.db.scalar(select(Product).where(Product.store_id == store_id, Product.slug == slug))

    async def get_by_sku(self, store_id: int, sku: str) -> Product | None:
        return await self.db.scalar(select(Product).where(Product.store_id == store_id, Product.sku == sku))

    async def create(self, **values) -> Product:
        product = Product(**values)
        self.db.add(product)
        await self.db.flush()
        return product

    async def delete(self, product: Product) -> None:
        await self.db.delete(product)
