import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models.identity import User
from app.modules.catalogue.repositories.category import CategoryRepository
from app.modules.catalogue.repositories.product import ProductRepository
from app.modules.catalogue.schemas.product import ProductCreate, ProductUpdate
from app.modules.catalogue.services.context import resolve_store


class ProductService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = ProductRepository(db)
        self.categories = CategoryRepository(db)

    async def list(self, user: User, tenant_public_id: str, offset: int, limit: int):
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.read")
        return await self.repository.list(store.id, offset, limit)

    async def get(self, user: User, tenant_public_id: str, public_id: str):
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.read")
        product = await self.repository.get(store.id, public_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    async def create(self, user: User, tenant_public_id: str, payload: ProductCreate):
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.manage")
        if payload.currency != store.currency:
            raise HTTPException(status_code=422, detail=f"Product currency must match the store currency ({store.currency})")
        category_id = None
        if payload.category_public_id:
            category = await self.categories.get(store.id, payload.category_public_id)
            if category is None:
                raise HTTPException(status_code=422, detail="Category not found")
            category_id = category.id
        if await self.repository.get_by_slug(store.id, payload.slug):
            raise HTTPException(status_code=409, detail="Product slug already exists")
        if payload.sku and await self.repository.get_by_sku(store.id, payload.sku):
            raise HTTPException(status_code=409, detail="Product SKU already exists")
        try:
            product = await self.repository.create(public_id=uuid.uuid4().hex, store_id=store.id, category_id=category_id, **payload.model_dump(exclude={"category_public_id"}))
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status_code=409, detail="Product could not be created with the supplied values") from None
        return await self.repository.get(store.id, product.public_id)

    async def update(self, user: User, tenant_public_id: str, public_id: str, payload: ProductUpdate):
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.manage")
        product = await self.repository.get(store.id, public_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        values = payload.model_dump(exclude_unset=True)
        if "currency" in values and values["currency"] != store.currency:
            raise HTTPException(status_code=422, detail=f"Product currency must match the store currency ({store.currency})")
        if "slug" in values and values["slug"] != product.slug and await self.repository.get_by_slug(store.id, values["slug"]):
            raise HTTPException(status_code=409, detail="Product slug already exists")
        if "sku" in values and values["sku"] and values["sku"] != product.sku and await self.repository.get_by_sku(store.id, values["sku"]):
            raise HTTPException(status_code=409, detail="Product SKU already exists")
        if "category_public_id" in values:
            category_public_id = values.pop("category_public_id")
            if category_public_id is None:
                product.category_id = None
            else:
                category = await self.categories.get(store.id, category_public_id)
                if category is None:
                    raise HTTPException(status_code=422, detail="Category not found")
                product.category_id = category.id
        if "price_minor" in values and "compare_at_price_minor" not in values and product.compare_at_price_minor is not None and product.compare_at_price_minor < values["price_minor"]:
            raise HTTPException(status_code=422, detail="compare_at_price_minor must be greater than or equal to price_minor")
        if "compare_at_price_minor" in values and values["compare_at_price_minor"] is not None:
            price = values.get("price_minor", product.price_minor)
            if values["compare_at_price_minor"] < price:
                raise HTTPException(status_code=422, detail="compare_at_price_minor must be greater than or equal to price_minor")
        for key, value in values.items():
            setattr(product, key, value)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status_code=409, detail="Product could not be updated with the supplied values") from None
        return await self.repository.get(store.id, public_id)

    async def delete(self, user: User, tenant_public_id: str, public_id: str) -> None:
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.manage")
        product = await self.repository.get(store.id, public_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        await self.repository.delete(product)
        await self.db.commit()
