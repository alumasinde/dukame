from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models.identity import User
from app.modules.auth.security import get_current_user
from app.modules.catalogue.schemas.option import OptionCreate, OptionResponse, OptionUpdate, OptionValueCreate, OptionValueResponse, OptionValueUpdate
from app.modules.catalogue.services.options import OptionService

router = APIRouter(prefix="/tenants/{tenant_public_id}/options", tags=["catalogue"])


def value_response(value) -> OptionValueResponse:
    return OptionValueResponse(public_id=value.public_id, name=value.name, slug=value.slug, status=value.status, sort_order=value.sort_order)


def option_response(option) -> OptionResponse:
    return OptionResponse(public_id=option.public_id, name=option.name, slug=option.slug, status=option.status, sort_order=option.sort_order, values=[value_response(value) for value in option.values])


@router.get("", response_model=list[OptionResponse])
async def list_options(tenant_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return [option_response(option) for option in await OptionService(db).list(user, tenant_public_id)]


@router.post("", response_model=OptionResponse, status_code=status.HTTP_201_CREATED)
async def create_option(tenant_public_id: str, payload: OptionCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return option_response(await OptionService(db).create(user, tenant_public_id, payload))


@router.put("/{option_public_id}", response_model=OptionResponse)
async def update_option(tenant_public_id: str, option_public_id: str, payload: OptionUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return option_response(await OptionService(db).update(user, tenant_public_id, option_public_id, payload))


@router.delete("/{option_public_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_option(tenant_public_id: str, option_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Response:
    await OptionService(db).delete(user, tenant_public_id, option_public_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{option_public_id}/values", response_model=OptionValueResponse, status_code=status.HTTP_201_CREATED)
async def add_value(tenant_public_id: str, option_public_id: str, payload: OptionValueCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return value_response(await OptionService(db).add_value(user, tenant_public_id, option_public_id, payload))


@router.put("/{option_public_id}/values/{value_public_id}", response_model=OptionValueResponse)
async def update_value(tenant_public_id: str, option_public_id: str, value_public_id: str, payload: OptionValueUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return value_response(await OptionService(db).update_value(user, tenant_public_id, option_public_id, value_public_id, payload))


@router.delete("/{option_public_id}/values/{value_public_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_value(tenant_public_id: str, option_public_id: str, value_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Response:
    await OptionService(db).delete_value(user, tenant_public_id, option_public_id, value_public_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
