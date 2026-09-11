import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models.identity import User
from app.modules.catalogue.repositories.category import CategoryRepository
from app.modules.catalogue.schemas.category import CategoryCreate, CategoryUpdate
from app.modules.catalogue.services.context import resolve_store


class CategoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = CategoryRepository(db)

    async def list(self, user: User, tenant_public_id: str, offset: int, limit: int):
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.read")
        return await self.repository.list(store.id, offset, limit)

    async def get(self, user: User, tenant_public_id: str, public_id: str):
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.read")
        category = await self.repository.get(store.id, public_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        return category

    async def create(self, user: User, tenant_public_id: str, payload: CategoryCreate):
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.manage")
        parent_id = None
        if payload.parent_public_id:
            parent = await self.repository.get(store.id, payload.parent_public_id)
            if parent is None:
                raise HTTPException(status_code=422, detail="Parent category not found")
            parent_id = parent.id
        if await self.repository.get_by_slug(store.id, payload.slug):
            raise HTTPException(status_code=409, detail="Category slug already exists")
        try:
            category = await self.repository.create(public_id=uuid.uuid4().hex, store_id=store.id, parent_id=parent_id, **payload.model_dump(exclude={"parent_public_id"}))
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status_code=409, detail="Category could not be created with the supplied values") from None
        return await self.repository.get(store.id, category.public_id)

    async def update(self, user: User, tenant_public_id: str, public_id: str, payload: CategoryUpdate):
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.manage")
        category = await self.repository.get(store.id, public_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        values = payload.model_dump(exclude_unset=True)
        if "slug" in values and values["slug"] != category.slug and await self.repository.get_by_slug(store.id, values["slug"]):
            raise HTTPException(status_code=409, detail="Category slug already exists")
        if "parent_public_id" in values:
            parent_public_id = values.pop("parent_public_id")
            if parent_public_id is None:
                category.parent_id = None
            else:
                parent = await self.repository.get(store.id, parent_public_id)
                if parent is None:
                    raise HTTPException(status_code=422, detail="Parent category not found")
                if parent.id == category.id:
                    raise HTTPException(status_code=422, detail="A category cannot be its own parent")
                ancestor = parent
                while ancestor.parent_id is not None:
                    ancestor = await self.db.get(type(category), ancestor.parent_id)
                    if ancestor is None:
                        break
                    if ancestor.id == category.id:
                        raise HTTPException(status_code=422, detail="Category hierarchy cannot contain a cycle")
                category.parent_id = parent.id
        for key, value in values.items():
            setattr(category, key, value)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status_code=409, detail="Category could not be updated with the supplied values") from None
        return await self.repository.get(store.id, public_id)

    async def delete(self, user: User, tenant_public_id: str, public_id: str) -> None:
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.manage")
        category = await self.repository.get(store.id, public_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        if await self.repository.count_children(store.id, category.id):
            raise HTTPException(status_code=409, detail="Move or delete child categories before deleting this category")
        await self.repository.delete(category)
        await self.db.commit()
