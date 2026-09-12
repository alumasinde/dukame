from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models.identity import User
from app.modules.auth.security import get_current_user
from app.modules.customers.models.customer import Customer
from app.modules.customers.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.modules.customers.services.customer import CustomerService

router = APIRouter(prefix="/tenants/{tenant_public_id}/customers", tags=["customers"])


def to_response(result: tuple[Customer, int]) -> CustomerResponse:
    customer, order_count = result
    return CustomerResponse(
        public_id=customer.public_id,
        first_name=customer.first_name,
        last_name=customer.last_name,
        phone=customer.phone,
        email=customer.email,
        notes=customer.notes,
        is_active=customer.is_active,
        order_count=order_count,
    )


@router.get("", response_model=list[CustomerResponse])
async def list_customers(
    tenant_public_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    search: str | None = Query(default=None, max_length=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CustomerResponse]:
    return [to_response(item) for item in await CustomerService(db).list(user, tenant_public_id, offset, limit, search)]


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    tenant_public_id: str,
    payload: CustomerCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    return to_response(await CustomerService(db).create(user, tenant_public_id, payload))


@router.get("/{customer_public_id}", response_model=CustomerResponse)
async def get_customer(
    tenant_public_id: str,
    customer_public_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    return to_response(await CustomerService(db).get(user, tenant_public_id, customer_public_id))


@router.put("/{customer_public_id}", response_model=CustomerResponse)
async def update_customer(
    tenant_public_id: str,
    customer_public_id: str,
    payload: CustomerUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    return to_response(await CustomerService(db).update(user, tenant_public_id, customer_public_id, payload))
