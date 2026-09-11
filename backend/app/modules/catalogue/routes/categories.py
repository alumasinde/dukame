from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models.identity import User
from app.modules.auth.security import get_current_user
from app.modules.catalogue.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.modules.catalogue.services.category import CategoryService

router = APIRouter(prefix="/tenants/{tenant_public_id}/categories", tags=["catalogue"])


def to_response(category) -> CategoryResponse:
    return CategoryResponse(
        public_id=category.public_id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        parent_public_id=category.parent.public_id if category.parent else None,
        status=category.status,
        sort_order=category.sort_order,
    )


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    tenant_public_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CategoryResponse]:
    categories = await CategoryService(db).list(user, tenant_public_id, offset, limit)
    return [to_response(category) for category in categories]


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(tenant_public_id: str, payload: CategoryCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> CategoryResponse:
    return to_response(await CategoryService(db).create(user, tenant_public_id, payload))


@router.get("/{category_public_id}", response_model=CategoryResponse)
async def get_category(tenant_public_id: str, category_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> CategoryResponse:
    return to_response(await CategoryService(db).get(user, tenant_public_id, category_public_id))


@router.put("/{category_public_id}", response_model=CategoryResponse)
async def update_category(tenant_public_id: str, category_public_id: str, payload: CategoryUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> CategoryResponse:
    return to_response(await CategoryService(db).update(user, tenant_public_id, category_public_id, payload))


@router.delete("/{category_public_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(tenant_public_id: str, category_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Response:
    await CategoryService(db).delete(user, tenant_public_id, category_public_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
