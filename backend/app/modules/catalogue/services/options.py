import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models.identity import User
from app.modules.catalogue.repositories.option import OptionRepository
from app.modules.catalogue.repositories.option_value import OptionValueRepository
from app.modules.catalogue.schemas.option import OptionCreate, OptionUpdate, OptionValueCreate, OptionValueUpdate
from app.modules.catalogue.services.context import resolve_store


class OptionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.options = OptionRepository(db)
        self.values = OptionValueRepository(db)

    async def list(self, user: User, tenant_public_id: str):
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.read")
        return await self.options.list(store.id)

    async def create(self, user: User, tenant_public_id: str, payload: OptionCreate):
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.manage")
        if await self.options.get_by_slug(store.id, payload.slug):
            raise HTTPException(status_code=409, detail="Option slug already exists")
        try:
            option = await self.options.create(public_id=uuid.uuid4().hex, store_id=store.id, **payload.model_dump())
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status_code=409, detail="Option could not be created with the supplied values") from None
        return await self.options.get(store.id, option.public_id)

    async def update(self, user: User, tenant_public_id: str, public_id: str, payload: OptionUpdate):
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.manage")
        option = await self.options.get(store.id, public_id)
        if option is None:
            raise HTTPException(status_code=404, detail="Option not found")
        values = payload.model_dump(exclude_unset=True)
        if "slug" in values and values["slug"] != option.slug and await self.options.get_by_slug(store.id, values["slug"]):
            raise HTTPException(status_code=409, detail="Option slug already exists")
        for key, value in values.items():
            setattr(option, key, value)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status_code=409, detail="Option could not be updated with the supplied values") from None
        return await self.options.get(store.id, option.public_id)

    async def delete(self, user: User, tenant_public_id: str, public_id: str) -> None:
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.manage")
        option = await self.options.get(store.id, public_id)
        if option is None:
            raise HTTPException(status_code=404, detail="Option not found")
        if await self.values.count_option_variant_links(option.id):
            raise HTTPException(status_code=409, detail="This option is used by product variants and cannot be deleted")
        await self.options.delete(option)
        await self.db.commit()

    async def add_value(self, user: User, tenant_public_id: str, option_public_id: str, payload: OptionValueCreate):
        store = await resolve_store(self.db, tenant_public_id, "catalogue.manage")
        option = await self.options.get(store.id, option_public_id)
        if option is None:
            raise HTTPException(status_code=404, detail="Option not found")
        if await self.values.get_by_slug(option.id, payload.slug):
            raise HTTPException(status_code=409, detail="Option value slug already exists")
        try:
            value = await self.values.create(public_id=uuid.uuid4().hex, option_id=option.id, **payload.model_dump())
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status_code=409, detail="Option value could not be created with the supplied values") from None
        return value

    async def update_value(self, user: User, tenant_public_id: str, option_public_id: str, value_public_id: str, payload: OptionValueUpdate):
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.manage")
        option = await self.options.get(store.id, option_public_id)
        if option is None:
            raise HTTPException(status_code=404, detail="Option not found")
        value = await self.values.get(option.id, value_public_id)
        if value is None:
            raise HTTPException(status_code=404, detail="Option value not found")
        values = payload.model_dump(exclude_unset=True)
        if "slug" in values and values["slug"] != value.slug and await self.values.get_by_slug(option.id, values["slug"]):
            raise HTTPException(status_code=409, detail="Option value slug already exists")
        for key, item in values.items():
            setattr(value, key, item)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status_code=409, detail="Option value could not be updated with the supplied values") from None
        return value

    async def delete_value(self, user: User, tenant_public_id: str, option_public_id: str, value_public_id: str) -> None:
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.manage")
        option = await self.options.get(store.id, option_public_id)
        if option is None:
            raise HTTPException(status_code=404, detail="Option not found")
        value = await self.values.get(option.id, value_public_id)
        if value is None:
            raise HTTPException(status_code=404, detail="Option value not found")
        if await self.values.count_variant_links(value.id):
            raise HTTPException(status_code=409, detail="This option value is used by product variants and cannot be deleted")
        await self.values.delete(value)
        await self.db.commit()
