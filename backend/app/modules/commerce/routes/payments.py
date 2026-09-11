from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models.identity import User
from app.modules.auth.security import get_current_user
from app.modules.catalogue.services.context import resolve_store
from app.modules.commerce.payment_service import PaymentService, payment_response
from app.modules.commerce.schemas import PaymentMethodCreate, PaymentMethodResponse, PaymentResponse
from app.modules.storefront.routes import get_active_store

router = APIRouter(tags=["payments"])


@router.get("/storefront/{store_slug}/payment-methods", response_model=list[PaymentMethodResponse])
async def list_storefront_payment_methods(store_slug: str, db: AsyncSession = Depends(get_db)) -> list[PaymentMethodResponse]:
    store = await get_active_store(db, store_slug)
    methods = await PaymentService(db).list_public_methods(store)
    return [PaymentMethodResponse(public_id=item.public_id, code=item.code, name=item.name, is_enabled=True, instructions=item.instructions) for item in methods]


@router.get("/tenants/{tenant_public_id}/payment-methods", response_model=list[PaymentMethodResponse])
async def list_payment_methods(tenant_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[PaymentMethodResponse]:
    store = await resolve_store(db, user, tenant_public_id, "payments.read")
    methods = await PaymentService(db).list_public_methods(store)
    return [PaymentMethodResponse(public_id=item.public_id, code=item.code, name=item.name, is_enabled=item.is_enabled, instructions=item.instructions) for item in methods]


@router.post("/tenants/{tenant_public_id}/payment-methods", response_model=PaymentMethodResponse)
async def create_payment_method(tenant_public_id: str, payload: PaymentMethodCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> PaymentMethodResponse:
    method, callback_token, callback_url = await PaymentService(db).create_method(user, tenant_public_id, payload.code, payload.name, payload.instructions, payload.is_enabled, payload.config)
    return PaymentMethodResponse(public_id=method.public_id, code=method.code, name=method.name, is_enabled=method.is_enabled, instructions=method.instructions, callback_url=callback_url, callback_token=callback_token)


@router.patch("/tenants/{tenant_public_id}/payments/{payment_public_id}/cash-paid", response_model=PaymentResponse)
async def mark_cash_payment_paid(tenant_public_id: str, payment_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> PaymentResponse:
    payment = await PaymentService(db).set_cash_paid(user, tenant_public_id, payment_public_id)
    return PaymentResponse.model_validate(payment_response(payment))


@router.post("/payments/mpesa/callback/{callback_token}", status_code=204)
async def mpesa_callback(callback_token: str, payload: dict[str, Any], db: AsyncSession = Depends(get_db)) -> None:
    await PaymentService(db).callback(callback_token, payload)


@router.get("/tenants/{tenant_public_id}/orders/{order_public_id}/payment", response_model=PaymentResponse)
async def get_order_payment(tenant_public_id: str, order_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> PaymentResponse:
    store = await resolve_store(db, user, tenant_public_id, "payments.read")
    payment = await PaymentService(db).get_order_payment(store, order_public_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return PaymentResponse.model_validate(payment_response(payment))
