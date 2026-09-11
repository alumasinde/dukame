import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models.identity import User
from app.modules.catalogue.models.product import Product
from app.modules.catalogue.repositories.media import ProductMediaRepository
from app.modules.catalogue.schemas.media import ProductMediaCreate, ProductMediaUpdate
from app.modules.catalogue.services.context import resolve_store


class ProductMediaService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.media = ProductMediaRepository(db)

    async def _product(self, store_id: int, public_id: str) -> Product:
        product = await self.db.scalar(select(Product).where(Product.store_id == store_id, Product.public_id == public_id))
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    async def list(self, user: User, tenant_public_id: str, product_public_id: str):
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.read")
        product = await self._product(store.id, product_public_id)
        return await self.media.list(product.id)

    async def create(self, user: User, tenant_public_id: str, product_public_id: str, payload: ProductMediaCreate):
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.manage")
        product = await self._product(store.id, product_public_id)
        media = await self.media.create(public_id=uuid.uuid4().hex, store_id=store.id, product_id=product.id, **payload.model_dump(mode="json"))
        await self.db.commit()
        return await self.media.get(product.id, media.public_id)

    async def update(self, user: User, tenant_public_id: str, product_public_id: str, public_id: str, payload: ProductMediaUpdate):
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.manage")
        product = await self._product(store.id, product_public_id)
        media = await self.media.get(product.id, public_id)
        if media is None:
            raise HTTPException(status_code=404, detail="Media item not found")
        for key, value in payload.model_dump(exclude_unset=True, mode="json").items():
            setattr(media, key, value)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status_code=409, detail="Media could not be updated") from None
        return await self.media.get(product.id, media.public_id)

    async def delete(self, user: User, tenant_public_id: str, product_public_id: str, public_id: str) -> None:
        store = await resolve_store(self.db, user, tenant_public_id, "catalogue.manage")
        product = await self._product(store.id, product_public_id)
        media = await self.media.get(product.id, public_id)
        if media is None:
            raise HTTPException(status_code=404, detail="Media item not found")
        await self.media.delete(media)
        await self.db.commit()
