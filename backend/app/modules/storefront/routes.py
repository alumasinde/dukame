from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.modules.catalogue.models.category import Category
from app.modules.catalogue.models.product import Product
from app.modules.catalogue.models.store import Store
from app.modules.storefront.schemas import StorefrontProductResponse, StorefrontResponse

router = APIRouter(prefix="/storefront", tags=["storefront"])


def category_response(category: Category) -> dict[str, str | None]:
    return {
        "public_id": category.public_id,
        "name": category.name,
        "slug": category.slug,
        "parent_public_id": category.parent.public_id if category.parent else None,
    }


def product_response(product: Product) -> StorefrontProductResponse:
    return StorefrontProductResponse(
        public_id=product.public_id,
        name=product.name,
        slug=product.slug,
        description=product.description,
        price_minor=product.price_minor,
        compare_at_price_minor=product.compare_at_price_minor,
        currency=product.currency,
        category=(category_response(product.category) if product.category else None),
        media=[
            {"url": item.url, "alt_text": item.alt_text}
            for item in product.media
            if item.status == "active" and item.media_type == "image"
        ],
    )


async def get_active_store(db: AsyncSession, slug: str) -> Store:
    store = await db.scalar(select(Store).where(Store.slug == slug, Store.status == "active"))
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.get("/{store_slug}", response_model=StorefrontResponse)
async def get_storefront(store_slug: str, db: AsyncSession = Depends(get_db)) -> StorefrontResponse:
    store = await get_active_store(db, store_slug)
    products = list(
        (
            await db.scalars(
                select(Product)
                .options(
                    selectinload(Product.media),
                    selectinload(Product.category).selectinload(Category.parent),
                )
                .where(Product.store_id == store.id, Product.status == "active")
                .order_by(Product.created_at.desc())
            )
        ).all()
    )
    categories = list(
        (
            await db.scalars(
                select(Category)
                .options(selectinload(Category.parent))
                .where(Category.store_id == store.id, Category.status == "active")
                .order_by(Category.sort_order.asc(), Category.name.asc())
            )
        ).all()
    )
    return StorefrontResponse(
        public_id=store.public_id,
        name=store.name,
        slug=store.slug,
        description=store.description,
        currency=store.currency,
        categories=[category_response(item) for item in categories],
        products=[product_response(product) for product in products],
    )


@router.get("/{store_slug}/products/{product_slug}", response_model=StorefrontProductResponse)
async def get_storefront_product(
    store_slug: str,
    product_slug: str,
    db: AsyncSession = Depends(get_db),
) -> StorefrontProductResponse:
    store = await get_active_store(db, store_slug)
    product = await db.scalar(
        select(Product)
        .options(
            selectinload(Product.media),
            selectinload(Product.category).selectinload(Category.parent),
        )
        .where(
            Product.store_id == store.id,
            Product.slug == product_slug,
            Product.status == "active",
        )
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product_response(product)
