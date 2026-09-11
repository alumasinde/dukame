from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalogue.models.option import ProductOption


class OptionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, store_id: int) -> list[ProductOption]:
        result = await self.db.scalars(
            select(ProductOption)
            .options(selectinload(ProductOption.values))
            .where(ProductOption.store_id == store_id)
            .order_by(ProductOption.sort_order, ProductOption.name)
        )
        return list(result.all())

    async def get(self, store_id: int, public_id: str) -> ProductOption | None:
        return await self.db.scalar(
            select(ProductOption)
            .options(selectinload(ProductOption.values))
            .where(ProductOption.store_id == store_id, ProductOption.public_id == public_id)
        )

    async def get_by_slug(self, store_id: int, slug: str) -> ProductOption | None:
        return await self.db.scalar(select(ProductOption).where(ProductOption.store_id == store_id, ProductOption.slug == slug))

    async def create(self, **values) -> ProductOption:
        option = ProductOption(**values)
        self.db.add(option)
        await self.db.flush()
        return option

    async def delete(self, option: ProductOption) -> None:
        await self.db.delete(option)
