from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models.identity import User
from app.modules.auth.security import get_current_user
from app.modules.catalogue.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.modules.catalogue.services.product import ProductService

router = APIRouter(prefix="/tenants/{tenant_public_id}/products", tags=["catalogue"])


def to_response(product) -> ProductResponse:
    return ProductResponse(
        public_id=product.public_id,
        name=product.name,
        slug=product.slug,
        description=product.description,
        category_public_id=product.category.public_id if product.category else None,
        sku=product.sku,
        price_minor=product.price_minor,
        compare_at_price_minor=product.compare_at_price_minor,
        currency=product.currency,
        inventory_tracking=product.inventory_tracking,
        inventory_quantity=product.inventory_quantity,
        status=product.status,
    )


@router.get("", response_model=list[ProductResponse])
async def list_products(
    tenant_public_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProductResponse]:
    products = await ProductService(db).list(user, tenant_public_id, offset, limit)
    return [to_response(product) for product in products]


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(tenant_public_id: str, payload: ProductCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> ProductResponse:
    return to_response(await ProductService(db).create(user, tenant_public_id, payload))


@router.get("/{product_public_id}", response_model=ProductResponse)
async def get_product(tenant_public_id: str, product_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> ProductResponse:
    return to_response(await ProductService(db).get(user, tenant_public_id, product_public_id))


@router.put("/{product_public_id}", response_model=ProductResponse)
async def update_product(tenant_public_id: str, product_public_id: str, payload: ProductUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> ProductResponse:
    return to_response(await ProductService(db).update(user, tenant_public_id, product_public_id, payload))


@router.delete("/{product_public_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(tenant_public_id: str, product_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Response:
    await ProductService(db).delete(user, tenant_public_id, product_public_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
