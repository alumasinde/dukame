from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models.identity import User
from app.modules.auth.security import get_current_user
from app.modules.catalogue.schemas.variant import VariantCreate, VariantResponse, VariantUpdate
from app.modules.catalogue.services.variants import VariantService

router = APIRouter(prefix="/tenants/{tenant_public_id}/products/{product_public_id}/variants", tags=["catalogue"])


def to_response(variant) -> VariantResponse:
    return VariantResponse(
        public_id=variant.public_id,
        sku=variant.sku,
        price_minor=variant.price_minor,
        compare_at_price_minor=variant.compare_at_price_minor,
        inventory_tracking=variant.inventory_tracking,
        inventory_quantity=variant.inventory_quantity,
        status=variant.status,
        option_value_public_ids=[link.option_value.public_id for link in variant.option_value_links],
    )


@router.get("", response_model=list[VariantResponse])
async def list_variants(tenant_public_id: str, product_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return [to_response(item) for item in await VariantService(db).list(user, tenant_public_id, product_public_id)]


@router.post("", response_model=VariantResponse, status_code=status.HTTP_201_CREATED)
async def create_variant(tenant_public_id: str, product_public_id: str, payload: VariantCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return to_response(await VariantService(db).create(user, tenant_public_id, product_public_id, payload))


@router.put("/{variant_public_id}", response_model=VariantResponse)
async def update_variant(tenant_public_id: str, product_public_id: str, variant_public_id: str, payload: VariantUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return to_response(await VariantService(db).update(user, tenant_public_id, product_public_id, variant_public_id, payload))


@router.delete("/{variant_public_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variant(tenant_public_id: str, product_public_id: str, variant_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Response:
    await VariantService(db).delete(user, tenant_public_id, product_public_id, variant_public_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
