from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.modules.auth.models.identity import User
from app.modules.auth.security import get_current_user
from app.modules.catalogue.services.context import resolve_store
from app.modules.commerce.models.payment import Payment
from app.modules.commerce.models.payment_method import PaymentMethod
from app.modules.commerce.payment_service import PaymentService, payment_list_response, payment_response
from app.modules.commerce.schemas import PaymentListItemResponse, PaymentMethodCreate, PaymentMethodResponse, PaymentMethodUpdate, PaymentResponse
from app.modules.storefront.routes import get_active_store

router = APIRouter(tags=["payments"])


def method_response(method: PaymentMethod, callback_url: str | None = None, callback_token: str | None = None) -> PaymentMethodResponse:
    display_code = "mpesa" if method.code == "mpesa_paybill" else method.code
    return PaymentMethodResponse(public_id=method.public_id, code=display_code, name=method.name, is_enabled=method.is_enabled, instructions=method.instructions, callback_url=callback_url, callback_token=callback_token)


@router.get("/storefront/{store_slug}/payment-methods", response_model=list[PaymentMethodResponse])
async def list_storefront_payment_methods(store_slug: str, db: AsyncSession = Depends(get_db)) -> list[PaymentMethodResponse]:
    store = await get_active_store(db, store_slug)
    methods = await PaymentService(db).list_public_methods(store)
    return [method_response(item) for item in methods]


@router.get("/tenants/{tenant_public_id}/payment-methods", response_model=list[PaymentMethodResponse])
async def list_payment_methods(tenant_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[PaymentMethodResponse]:
    methods = await PaymentService(db).list_methods(user, tenant_public_id)
    return [method_response(item) for item in methods]


@router.post("/tenants/{tenant_public_id}/payment-methods", response_model=PaymentMethodResponse)
async def create_payment_method(tenant_public_id: str, payload: PaymentMethodCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> PaymentMethodResponse:
    normalized_code = payload.code.strip().lower()
    store = await resolve_store(db, user, tenant_public_id, "payments.manage")
    if normalized_code == "mpesa_paybill":
        config = payload.config or {}
        paybill = str(config.get("paybill_number", "")).strip()
        account_mode = str(config.get("account_mode", "order_number")).strip()
        if not paybill.isdigit() or not 5 <= len(paybill) <= 8:
            raise HTTPException(status_code=422, detail="Enter a valid M-Pesa Paybill number")
        if account_mode not in {"order_number", "customer_reference", "fixed"}:
            raise HTTPException(status_code=422, detail="Invalid Paybill account mode")
        if await db.scalar(select(PaymentMethod.id).where(PaymentMethod.store_id == store.id, PaymentMethod.code == normalized_code)):
            raise HTTPException(status_code=409, detail="M-Pesa Paybill is already configured")
        from app.modules.commerce.payment_security import encrypt_config
        instructions = payload.instructions.strip() if payload.instructions else f"Pay via M-Pesa Paybill {paybill}. Use your DukaMe order number as the account reference."
        method = PaymentMethod(public_id=secrets.token_hex(16), store_id=store.id, code=normalized_code, name=payload.name.strip() or "M-Pesa", is_enabled=payload.is_enabled, sort_order=20, instructions=instructions, config_encrypted=encrypt_config({"paybill_number": paybill, "account_mode": account_mode, "account_reference": str(config.get("account_reference", "")).strip()}))
        db.add(method)
        await db.commit()
        return method_response(method)
    if normalized_code == "card":
        if await db.scalar(select(PaymentMethod.id).where(PaymentMethod.store_id == store.id, PaymentMethod.code == "card")):
            raise HTTPException(status_code=409, detail="Payment method already exists")
        method = PaymentMethod(public_id=secrets.token_hex(16), store_id=store.id, code="card", name=payload.name.strip(), is_enabled=payload.is_enabled, sort_order=30, instructions=payload.instructions.strip() if payload.instructions else "Accept card payments using your card terminal or configured card processor.")
        db.add(method)
        await db.commit()
        return method_response(method)
    method, callback_token, callback_url = await PaymentService(db).create_method(user, tenant_public_id, payload.code, payload.name, payload.instructions, payload.is_enabled, payload.config)
    return method_response(method, callback_url, callback_token)


@router.patch("/tenants/{tenant_public_id}/payment-methods/{method_public_id}", response_model=PaymentMethodResponse)
async def update_payment_method(tenant_public_id: str, method_public_id: str, payload: PaymentMethodUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> PaymentMethodResponse:
    store = await resolve_store(db, user, tenant_public_id, "payments.manage")
    method = await db.scalar(select(PaymentMethod).where(PaymentMethod.store_id == store.id, PaymentMethod.public_id == method_public_id))
    if method is None:
        raise HTTPException(status_code=404, detail="Payment method not found")
    if method.code == "mpesa_paybill":
        from app.modules.commerce.payment_security import decrypt_config, encrypt_config
        current = decrypt_config(method.config_encrypted)
        if payload.name is not None:
            method.name = payload.name.strip()
        if payload.instructions is not None:
            method.instructions = payload.instructions.strip() or None
        if payload.is_enabled is not None:
            method.is_enabled = payload.is_enabled
        if payload.config is not None:
            merged = {**current, **payload.config}
            paybill = str(merged.get("paybill_number", "")).strip()
            if not paybill.isdigit() or not 5 <= len(paybill) <= 8:
                raise HTTPException(status_code=422, detail="Enter a valid M-Pesa Paybill number")
            if str(merged.get("account_mode", "order_number")) not in {"order_number", "customer_reference", "fixed"}:
                raise HTTPException(status_code=422, detail="Invalid Paybill account mode")
            method.config_encrypted = encrypt_config(merged)
        await db.commit()
        return method_response(method)
    method, callback_url = await PaymentService(db).update_method(user, tenant_public_id, method_public_id, payload.name, payload.instructions, payload.is_enabled, payload.config)
    return method_response(method, callback_url)


@router.get("/tenants/{tenant_public_id}/payments", response_model=list[PaymentListItemResponse])
async def list_payments(tenant_public_id: str, offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100), status: str | None = Query(default=None, max_length=32), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[PaymentListItemResponse]:
    payments = await PaymentService(db).list_payments(user, tenant_public_id, offset, limit, status)
    return [PaymentListItemResponse.model_validate(payment_list_response(item)) for item in payments]


@router.get("/tenants/{tenant_public_id}/payments/{payment_public_id}", response_model=PaymentListItemResponse)
async def get_payment(tenant_public_id: str, payment_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> PaymentListItemResponse:
    payment = await PaymentService(db).get_payment(user, tenant_public_id, payment_public_id)
    return PaymentListItemResponse.model_validate(payment_list_response(payment))


@router.post("/tenants/{tenant_public_id}/payments/{payment_public_id}/retry", response_model=PaymentResponse)
async def retry_payment(tenant_public_id: str, payment_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> PaymentResponse:
    payment = await PaymentService(db).retry(user, tenant_public_id, payment_public_id)
    return PaymentResponse.model_validate(payment_response(payment))


@router.patch("/tenants/{tenant_public_id}/payments/{payment_public_id}/cash-paid", response_model=PaymentResponse)
async def mark_cash_payment_paid(tenant_public_id: str, payment_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> PaymentResponse:
    payment = await PaymentService(db).set_cash_paid(user, tenant_public_id, payment_public_id)
    return PaymentResponse.model_validate(payment_response(payment))


@router.patch("/tenants/{tenant_public_id}/payments/{payment_public_id}/manual-paid", response_model=PaymentResponse)
async def mark_manual_payment_paid(tenant_public_id: str, payment_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> PaymentResponse:
    store = await resolve_store(db, user, tenant_public_id, "payments.manage")
    payment = await db.scalar(select(Payment).options(selectinload(Payment.payment_method)).where(Payment.public_id == payment_public_id, Payment.store_id == store.id))
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.payment_method.code not in {"cash", "card", "mpesa_paybill"}:
        raise HTTPException(status_code=422, detail="Only manual cash, M-Pesa Paybill or card payments can be marked paid")
    if payment.status == "paid":
        return PaymentResponse.model_validate(payment_response(payment))
    if payment.status in {"refunded", "partially_refunded", "cancelled"}:
        raise HTTPException(status_code=409, detail="Payment cannot be marked paid")
    payment.status = "paid"
    payment.paid_at = datetime.now(UTC)
    payment.failure_reason = None
    await PaymentService(db)._confirm_order_after_payment(payment)
    await db.commit()
    payment = await PaymentService(db)._load_payment(payment.public_id)
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
