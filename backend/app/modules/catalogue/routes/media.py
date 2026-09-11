from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models.identity import User
from app.modules.auth.security import get_current_user
from app.modules.catalogue.schemas.media import ProductMediaCreate, ProductMediaResponse, ProductMediaUpdate
from app.modules.catalogue.services.media import ProductMediaService

router = APIRouter(prefix="/tenants/{tenant_public_id}/products/{product_public_id}/media", tags=["catalogue"])


def to_response(media) -> ProductMediaResponse:
    return ProductMediaResponse(
        public_id=media.public_id,
        url=media.url,
        alt_text=media.alt_text,
        media_type=media.media_type,
        sort_order=media.sort_order,
        status=media.status,
    )


@router.get("", response_model=list[ProductMediaResponse])
async def list_media(tenant_public_id: str, product_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return [to_response(item) for item in await ProductMediaService(db).list(user, tenant_public_id, product_public_id)]


@router.post("", response_model=ProductMediaResponse, status_code=status.HTTP_201_CREATED)
async def create_media(tenant_public_id: str, product_public_id: str, payload: ProductMediaCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return to_response(await ProductMediaService(db).create(user, tenant_public_id, product_public_id, payload))


@router.put("/{media_public_id}", response_model=ProductMediaResponse)
async def update_media(tenant_public_id: str, product_public_id: str, media_public_id: str, payload: ProductMediaUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return to_response(await ProductMediaService(db).update(user, tenant_public_id, product_public_id, media_public_id, payload))


@router.delete("/{media_public_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(tenant_public_id: str, product_public_id: str, media_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Response:
    await ProductMediaService(db).delete(user, tenant_public_id, product_public_id, media_public_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
