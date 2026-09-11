from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalogue.models.store import Store


class StoreRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_tenant_id(self, tenant_id: int) -> Store | None:
        return await self.db.scalar(select(Store).where(Store.tenant_id == tenant_id))

    async def get_by_public_id(self, tenant_id: int, public_id: str) -> Store | None:
        return await self.db.scalar(select(Store).where(Store.tenant_id == tenant_id, Store.public_id == public_id))

    async def get_by_slug(self, slug: str) -> Store | None:
        return await self.db.scalar(select(Store).where(Store.slug == slug))

    async def create(self, **values) -> Store:
        store = Store(**values)
        self.db.add(store)
        await self.db.flush()
        return store
