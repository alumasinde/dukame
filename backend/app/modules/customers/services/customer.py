from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models.identity import User
from app.modules.catalogue.services.context import resolve_store
from app.modules.commerce.audit_service import record_audit
from app.modules.commerce.notifications import normalize_phone
from app.modules.customers.models.customer import Customer
from app.modules.customers.repositories.customer import CustomerRepository
from app.modules.customers.schemas.customer import CustomerCreate, CustomerUpdate


class CustomerService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = CustomerRepository(db)

    @staticmethod
    def _phone(value: str) -> str:
        phone = normalize_phone(value)
        if not phone or len(phone) < 10:
            raise HTTPException(status_code=422, detail="Invalid customer phone number")
        return phone

    async def list(self, user: User, tenant_public_id: str, offset: int, limit: int, search: str | None):
        store = await resolve_store(self.db, user, tenant_public_id, "customers.read")
        return await self.repository.list(store.id, offset, limit, search)

    async def get(self, user: User, tenant_public_id: str, public_id: str):
        store = await resolve_store(self.db, user, tenant_public_id, "customers.read")
        result = await self.repository.get_with_order_count(store.id, public_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        return result

    async def create(self, user: User, tenant_public_id: str, payload: CustomerCreate):
        store = await resolve_store(self.db, user, tenant_public_id, "customers.manage")
        phone = self._phone(payload.phone)
        existing = await self.repository.get_by_phone(store.id, phone)
        if existing is not None:
            raise HTTPException(status_code=409, detail="A customer with this phone number already exists")
        customer = Customer(
            public_id=uuid.uuid4().hex,
            store_id=store.id,
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            phone=phone,
            email=str(payload.email).lower() if payload.email else None,
            notes=payload.notes.strip() if payload.notes else None,
        )
        self.db.add(customer)
        try:
            await self.db.flush()
            await record_audit(self.db, tenant_id=store.tenant_id, store_id=store.id, actor_user_id=user.id, action="customer.created", entity_type="customer", entity_public_id=customer.public_id, after={"first_name": customer.first_name, "last_name": customer.last_name, "phone": customer.phone, "email": customer.email, "is_active": customer.is_active})
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status_code=409, detail="A customer with this phone number already exists") from None
        return await self.repository.get_with_order_count(store.id, customer.public_id)

    async def update(self, user: User, tenant_public_id: str, public_id: str, payload: CustomerUpdate):
        store = await resolve_store(self.db, user, tenant_public_id, "customers.manage")
        customer = await self.repository.get(store.id, public_id)
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        before = {"first_name": customer.first_name, "last_name": customer.last_name, "phone": customer.phone, "email": customer.email, "notes": customer.notes, "is_active": customer.is_active}
        values = payload.model_dump(exclude_unset=True)
        if "phone" in values:
            phone = self._phone(values["phone"])
            duplicate = await self.repository.get_by_phone(store.id, phone)
            if duplicate is not None and duplicate.id != customer.id:
                raise HTTPException(status_code=409, detail="A customer with this phone number already exists")
            values["phone"] = phone
        if values.get("email"):
            values["email"] = str(values["email"]).lower()
        for key, value in values.items():
            if isinstance(value, str):
                value = value.strip()
            setattr(customer, key, value)
        after = {"first_name": customer.first_name, "last_name": customer.last_name, "phone": customer.phone, "email": customer.email, "notes": customer.notes, "is_active": customer.is_active}
        try:
            await record_audit(self.db, tenant_id=store.tenant_id, store_id=store.id, actor_user_id=user.id, action="customer.updated", entity_type="customer", entity_public_id=customer.public_id, before=before, after=after)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status_code=409, detail="Customer could not be updated with the supplied values") from None
        return await self.repository.get_with_order_count(store.id, customer.public_id)
