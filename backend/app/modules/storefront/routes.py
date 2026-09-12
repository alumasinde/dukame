from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.modules.catalogue.models.category import Category
from app.modules.catalogue.models.option_value import ProductOptionValue
from app.modules.catalogue.models.product import Product
from app.modules.catalogue.models.store import Store
from app.modules.catalogue.models.variant import ProductVariant
from app.modules.catalogue.models.variant_option_value import ProductVariantOptionValue
from app.modules.storefront.schemas import StorefrontProductResponse, StorefrontResponse

router = APIRouter(prefix="/storefront", tags=["storefront"])

SORT_OPTIONS = {"featured", "price_asc", "price_desc", "newest"}


def category_payload(category: Category | None) -> dict | None:
    if category is None:
        return None
    return {
        "public_id": category.public_id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "parent_public_id": category.parent.public_id if category.parent else None,
    }


def product_response(product: Product, include_variants: bool = False) -> StorefrontProductResponse:
    variants = []
    if include_variants:
        variants = [
            {
                "public_id": variant.public_id,
                "sku": variant.sku,
                "price_minor": variant.price_minor,
                "inventory_tracking": variant.inventory_tracking,
                "inventory_quantity": variant.inventory_quantity,
                "options": [
                    {
                        "option_public_id": link.option_value.option.public_id,
                        "option_name": link.option_value.option.name,
                        "value_public_id": link.option_value.public_id,
                        "value_name": link.option_value.name,
                    }
                    for link in variant.option_value_links
                    if link.option_value and link.option_value.option
                ],
            }
            for variant in product.variants
            if variant.status == "active"
        ]
    return StorefrontProductResponse(
        public_id=product.public_id,
        name=product.name,
        slug=product.slug,
        description=product.description,
        price_minor=product.price_minor,
        compare_at_price_minor=product.compare_at_price_minor,
        currency=product.currency,
        inventory_tracking=product.inventory_tracking,
        inventory_quantity=product.inventory_quantity,
        created_at=product.created_at,
        category=category_payload(product.category),
        media=[
            {"url": item.url, "alt_text": item.alt_text}
            for item in product.media
            if item.status == "active" and item.media_type == "image"
        ],
        variants=variants,
    )


async def get_active_store(db: AsyncSession, slug: str) -> Store:
    store = await db.scalar(select(Store).where(Store.slug == slug))
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")
    if store.status != "active":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "store_closed",
                "message": "This store is temporarily closed and is not accepting orders.",
                "store_name": store.name,
                "status": store.status,
            },
        )
    return store


@router.get("/{store_slug}", response_model=StorefrontResponse)
async def get_storefront(
    store_slug: str,
    db: AsyncSession = Depends(get_db),
    sort: str = Query(default="featured", description="featured | price_asc | price_desc | newest"),
    limit: int | None = Query(default=None, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, description="Category slug filter"),
) -> StorefrontResponse:
    store = await get_active_store(db, store_slug)
    sort_key = sort if sort in SORT_OPTIONS else "featured"

    filters = [Product.store_id == store.id, Product.status == "active"]

    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        filters.append(
            or_(
                func.lower(Product.name).like(term),
                func.lower(func.coalesce(Product.description, "")).like(term),
            )
        )

    if category and category.strip():
        cat = await db.scalar(
            select(Category).where(
                Category.store_id == store.id,
                Category.slug == category.strip(),
                Category.status == "active",
            )
        )
        if cat is not None:
            all_cats = list(
                (
                    await db.scalars(
                        select(Category).where(Category.store_id == store.id, Category.status == "active")
                    )
                ).all()
            )
            by_parent: dict[int | None, list[Category]] = {}
            for item in all_cats:
                by_parent.setdefault(item.parent_id, []).append(item)

            def collect(node_id: int) -> list[int]:
                ids = [node_id]
                for child in by_parent.get(node_id, []):
                    ids.extend(collect(child.id))
                return ids

            filters.append(Product.category_id.in_(collect(cat.id)))

    total = await db.scalar(select(func.count()).select_from(Product).where(*filters)) or 0

    if sort_key == "price_asc":
        order_clause = asc(Product.price_minor)
    elif sort_key == "price_desc":
        order_clause = desc(Product.price_minor)
    else:
        order_clause = desc(Product.created_at)

    query = (
        select(Product)
        .options(selectinload(Product.media), selectinload(Product.category).selectinload(Category.parent))
        .where(*filters)
        .order_by(order_clause)
    )
    if limit is not None:
        query = query.offset(offset).limit(limit)

    products = list((await db.scalars(query)).all())
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
        contact_phone=store.contact_phone,
        currency=store.currency,
        status=store.status,
        categories=[
            {
                "public_id": item.public_id,
                "name": item.name,
                "slug": item.slug,
                "description": item.description,
                "parent_public_id": item.parent.public_id if item.parent else None,
            }
            for item in categories
        ],
        products=[product_response(product) for product in products],
        total_products=int(total),
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
            selectinload(Product.variants)
            .selectinload(ProductVariant.option_value_links)
            .selectinload(ProductVariantOptionValue.option_value)
            .selectinload(ProductOptionValue.option),
        )
        .where(
            Product.store_id == store.id,
            Product.slug == product_slug,
            Product.status == "active",
        )
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product_response(product, include_variants=True)
