from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.commerce.models.order import Order
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
        return list((await self.db.execute(stmt)).all())

    async def get(self, store_id: int, public_id: str) -> Customer | None:
        return await self.db.scalar(select(Customer).where(Customer.store_id == store_id, Customer.public_id == public_id))

    async def get_by_phone(self, store_id: int, phone: str, lock: bool = False) -> Customer | None:
        stmt = select(Customer).where(Customer.store_id == store_id, Customer.phone == phone)
        if lock:
            stmt = stmt.with_for_update()
        return await self.db.scalar(stmt)

    async def get_with_order_count(self, store_id: int, public_id: str) -> tuple[Customer, int] | None:
        stmt = (
            select(Customer, func.count(Order.id).label("order_count"))
            .outerjoin(Order, Order.customer_id == Customer.id)
            .where(Customer.store_id == store_id, Customer.public_id == public_id)
            .group_by(Customer.id)
        )
        return (await self.db.execute(stmt)).one_or_none()
