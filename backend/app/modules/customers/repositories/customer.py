from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.commerce.models.order import Order
from app.modules.commerce.models.order_status import OrderStatus
from app.modules.customers.models.customer import Customer


class CustomerRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, store_id: int, offset: int, limit: int, search: str | None) -> list[tuple[Customer, int]]:
        order_count = func.count(Order.id).label("order_count")
        stmt = (
            select(Customer, order_count)
            .outerjoin(Order, Order.customer_id == Customer.id)
            .where(Customer.store_id == store_id)
            .group_by(Customer.id)
            .order_by(Customer.last_name.asc(), Customer.first_name.asc(), Customer.id.asc())
            .offset(offset)
            .limit(limit)
        )
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                Customer.first_name.like(term)
                | Customer.last_name.like(term)
                | Customer.phone.like(term)
                | Customer.email.like(term)
            )
        rows = (await self.db.execute(stmt)).all()
        return [(cast(Customer, row[0]), int(row[1])) for row in rows]

    async def get(self, store_id: int, public_id: str) -> Customer | None:
        return cast(Customer | None, await self.db.scalar(select(Customer).where(Customer.store_id == store_id, Customer.public_id == public_id)))

    async def get_by_phone(self, store_id: int, phone: str, lock: bool = False) -> Customer | None:
        stmt = select(Customer).where(Customer.store_id == store_id, Customer.phone == phone)
        if lock:
            stmt = stmt.with_for_update()
        return cast(Customer | None, await self.db.scalar(stmt))

    async def get_with_order_count(self, store_id: int, public_id: str) -> tuple[Customer, int] | None:
        stmt = (
            select(Customer, func.count(Order.id).label("order_count"))
            .outerjoin(Order, Order.customer_id == Customer.id)
            .where(Customer.store_id == store_id, Customer.public_id == public_id)
            .group_by(Customer.id)
        )
        row = (await self.db.execute(stmt)).one_or_none()
        if row is None:
            return None
        return cast(Customer, row[0]), int(row[1])

    async def list_orders(self, store_id: int, customer_id: int, offset: int, limit: int) -> list[Order]:
        stmt = (
            select(Order)
            .join(OrderStatus, OrderStatus.id == Order.status_id)
            .where(Order.store_id == store_id, Order.customer_id == customer_id)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list((await self.db.scalars(stmt)).all())
