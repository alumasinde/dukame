from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tenancy.models.business_type import BusinessType


async def list_business_types(db: AsyncSession) -> list[BusinessType]:
    result = await db.scalars(
        select(BusinessType)
        .where(BusinessType.is_active.is_(True))
        .order_by(BusinessType.sort_order, BusinessType.name)
    )
    return list(result.all())


async def get_business_type(db: AsyncSession, public_id: str) -> BusinessType | None:
    return await db.scalar(
        select(BusinessType).where(
            BusinessType.public_id == public_id,
            BusinessType.is_active.is_(True),
        )
    )
