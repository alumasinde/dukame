from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalogue.models.option_value import ProductOptionValue


class OptionValueRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, option_id: int, public_id: str) -> ProductOptionValue | None:
        return await self.db.scalar(select(ProductOptionValue).where(ProductOptionValue.option_id == option_id, ProductOptionValue.public_id == public_id))

    async def get_by_slug(self, option_id: int, slug: str) -> ProductOptionValue | None:
        return await self.db.scalar(select(ProductOptionValue).where(ProductOptionValue.option_id == option_id, ProductOptionValue.slug == slug))

    async def create(self, **values) -> ProductOptionValue:
        value = ProductOptionValue(**values)
        self.db.add(value)
        await self.db.flush()
        return value

    async def delete(self, value: ProductOptionValue) -> None:
        await self.db.delete(value)
