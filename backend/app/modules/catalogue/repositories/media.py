from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalogue.models.product_media import ProductMedia


class ProductMediaRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, product_id: int) -> list[ProductMedia]:
        result = await self.db.scalars(select(ProductMedia).where(ProductMedia.product_id == product_id).order_by(ProductMedia.sort_order, ProductMedia.created_at))
        return list(result.all())

    async def get(self, product_id: int, public_id: str) -> ProductMedia | None:
        return await self.db.scalar(select(ProductMedia).where(ProductMedia.product_id == product_id, ProductMedia.public_id == public_id))

    async def create(self, **values) -> ProductMedia:
        media = ProductMedia(**values)
        self.db.add(media)
        await self.db.flush()
        return media

    async def delete(self, media: ProductMedia) -> None:
        await self.db.delete(media)
