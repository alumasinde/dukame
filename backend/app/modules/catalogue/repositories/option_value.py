from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalogue.models.option_value import ProductOptionValue
from app.modules.catalogue.models.variant_option_value import ProductVariantOptionValue


class OptionValueRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, option_id: int, public_id: str) -> ProductOptionValue | None:
        return await self.db.scalar(select(ProductOptionValue).where(ProductOptionValue.option_id == option_id, ProductOptionValue.public_id == public_id))

    async def get_by_slug(self, option_id: int, slug: str) -> ProductOptionValue | None:
        return await self.db.scalar(select(ProductOptionValue).where(ProductOptionValue.option_id == option_id, ProductOptionValue.slug == slug))

    async def count_variant_links(self, value_id: int) -> int:
        return int(await self.db.scalar(select(func.count()).select_from(ProductVariantOptionValue).where(ProductVariantOptionValue.option_value_id == value_id)) or 0)

    async def count_option_variant_links(self, option_id: int) -> int:
        return int(await self.db.scalar(select(func.count()).select_from(ProductVariantOptionValue).join(ProductOptionValue, ProductOptionValue.id == ProductVariantOptionValue.option_value_id).where(ProductOptionValue.option_id == option_id)) or 0)

    async def create(self, **values) -> ProductOptionValue:
        value = ProductOptionValue(**values)
        self.db.add(value)
        await self.db.flush()
        return value

    async def delete(self, value: ProductOptionValue) -> None:
        await self.db.delete(value)
