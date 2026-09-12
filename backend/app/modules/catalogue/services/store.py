import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models.identity import User
from app.modules.catalogue.repositories.store import StoreRepository
from app.modules.catalogue.schemas.store import StoreCreate, StoreUpdate
from app.modules.catalogue.services.context import resolve_store
from app.modules.rbac.services.rbac import require_permission
from app.modules.subscriptions.services.gating import enforce_store_capacity
from app.modules.tenancy.services.tenant import get_tenant_by_public_id


class StoreService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = StoreRepository(db)

    async def get(self, user: User, tenant_public_id: str):
        return await resolve_store(self.db, user, tenant_public_id, "catalogue.read")

    async def create(self, user: User, tenant_public_id: str, payload: StoreCreate):
        tenant = await get_tenant_by_public_id(self.db, tenant_public_id)
        if tenant is None:
            raise HTTPException(status_code=404, detail="Tenant not found")
        await require_permission(self.db, user, tenant.id, "catalogue.manage")
        await enforce_store_capacity(self.db, tenant.id)
        if await self.repository.get_by_tenant_id(tenant.id):
            raise HTTPException(status_code=409, detail="Store already exists")
        if await self.repository.get_by_slug(payload.slug):
            raise HTTPException(status_code=409, detail="Store slug already exists")
        try:
            store = await self.repository.create(
                public_id=uuid.uuid4().hex, tenant_id=tenant.id, **payload.model_dump()
            )
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Store could not be created with the supplied values",
            ) from None
        await self.db.refresh(store)
        return store

    async def update(self, user: User, tenant_public_id: str, payload: StoreUpdate):
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.manage")
        values = payload.model_dump(exclude_unset=True)
        if (
            "slug" in values
            and values["slug"] != store.slug
            and await self.repository.get_by_slug(values["slug"])
        ):
            raise HTTPException(status_code=409, detail="Store slug already exists")
        for key, value in values.items():
            setattr(store, key, value)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Store could not be updated with the supplied values",
            ) from None
        await self.db.refresh(store)
        return store
