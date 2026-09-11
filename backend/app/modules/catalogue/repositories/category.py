from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalogue.models.category import Category


class CategoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, store_id: int, offset: int, limit: int) -> list[Category]:
        result = await self.db.scalars(
            select(Category)
            .options(selectinload(Category.parent))
            .where(Category.store_id == store_id)
            .order_by(Category.sort_order, Category.name)
            .offset(offset)
            .limit(limit)
        )
        return list(result.all())

    async def get(self, store_id: int, public_id: str) -> Category | None:
        return await self.db.scalar(
            select(Category).options(selectinload(Category.parent)).where(Category.store_id == store_id, Category.public_id == public_id)
        )

    async def get_by_slug(self, store_id: int, slug: str) -> Category | None:
        return await self.db.scalar(select(Category).where(Category.store_id == store_id, Category.slug == slug))

    async def count_children(self, store_id: int, category_id: int) -> int:
        return int(await self.db.scalar(select(func.count(Category.id)).where(Category.store_id == store_id, Category.parent_id == category_id)) or 0)

    async def create(self, **values) -> Category:
        category = Category(**values)
        self.db.add(category)
        await self.db.flush()
        return category

    async def delete(self, category: Category) -> None:
        await self.db.delete(category)
