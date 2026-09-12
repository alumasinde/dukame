from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.modules.auth.models.identity import User
from app.modules.auth.security import get_current_user
from app.modules.catalogue.services.context import resolve_store
from app.modules.commerce.models.payment import Payment
from app.modules.commerce.models.payment_method import PaymentMethod
from app.modules.commerce.payment_security import decrypt_config, encrypt_config
from app.modules.commerce.payment_service import PaymentService, payment_list_response, payment_response
from app.modules.commerce.schemas import PaymentListItemResponse, PaymentMethodCreate, PaymentMethodResponse, PaymentMethodUpdate, PaymentResponse
from app.modules.commerce.mpesa import MpesaClient, MpesaProviderError, validate_daraja_config
from app.modules.storefront.routes import get_active_store

router = APIRouter(tags=["payments"])


def _validate_mpesa_paybill_config(config: dict) -> tuple[str, str, str, str]:
    """Returns (payment_type, number, account_mode, account_reference), raises 422 on invalid input."""
    payment_type = str(config.get("payment_type", "paybill")).strip().lower()
    if payment_type not in {"paybill", "till"}:
        raise HTTPException(status_code=422, detail="Choose Paybill or Till Number")
    number_key = "paybill_number" if payment_type == "paybill" else "till_number"
    number = str(config.get(number_key, "")).strip()
    if not number.isdigit() or not 5 <= len(number) <= 8:
        raise HTTPException(status_code=422, detail=f"Enter a valid M-Pesa {'Paybill' if payment_type == 'paybill' else 'Till Number'}")
    account_mode = str(config.get("account_mode", "order_number")).strip()
    account_reference = str(config.get("account_reference", "")).strip()
    if payment_type == "till":
        account_mode, account_reference = "none", ""
    elif account_mode not in {"order_number", "customer_reference", "fixed"}:
        raise HTTPException(status_code=422, detail="Invalid Paybill account mode")
    if payment_type == "paybill" and account_mode == "fixed" and not account_reference:
        raise HTTPException(status_code=422, detail="Enter the fixed account reference")
    return payment_type, number, account_mode, account_reference


def method_response(method: PaymentMethod, callback_url: str | None = None, callback_token: str | None = None, merchant: bool = False) -> PaymentMethodResponse:
    display_code = "mpesa" if method.code == "mpesa_paybill" else method.code
    payment_type = method.payment_type
    if payment_type is None and method.code in {"mpesa", "mpesa_paybill"} and method.config_encrypted:
        config = decrypt_config(method.config_encrypted)
        payment_type = str(config.get("payment_type") or ("stk_push" if method.code == "mpesa" else "paybill"))
    return PaymentMethodResponse(public_id=method.public_id, code=display_code, name=method.name, is_enabled=method.is_enabled, payment_type=payment_type, instructions=method.instructions, callback_url=callback_url if merchant else None, callback_token=callback_token if merchant else None)


@router.get("/storefront/{store_slug}/payment-methods", response_model=list[PaymentMethodResponse])
async def list_storefront_payment_methods(store_slug: str, db: AsyncSession = Depends(get_db)) -> list[PaymentMethodResponse]:
    store = await get_active_store(db, store_slug)
    return [method_response(item) for item in await PaymentService(db).list_public_methods(store)]


@router.get("/tenants/{tenant_public_id}/payment-methods", response_model=list[PaymentMethodResponse])
async def list_payment_methods(tenant_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[PaymentMethodResponse]:
    methods = await PaymentService(db).list_methods(user, tenant_public_id)
    responses = []
    for item in methods:
        callback_url = callback_token = None
        if item.code == "mpesa" and item.config_encrypted:
            callback_token = decrypt_config(item.config_encrypted).get("callback_token")
            if callback_token:
                callback_url = PaymentService._callback_url(callback_token)
        responses.append(method_response(item, callback_url, callback_token, merchant=True))
    return responses


@router.post("/tenants/{tenant_public_id}/payment-methods", response_model=PaymentMethodResponse)
async def create_payment_method(tenant_public_id: str, payload: PaymentMethodCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> PaymentMethodResponse:
    normalized_code = payload.code.strip().lower()
    store = await resolve_store(db, user, tenant_public_id, "payments.manage")
    if normalized_code == "mpesa_paybill":
        config = payload.config or {}
        payment_type, number, account_mode, account_reference = _validate_mpesa_paybill_config(config)
        if await db.scalar(select(PaymentMethod.id).where(PaymentMethod.store_id == store.id, PaymentMethod.code == normalized_code, PaymentMethod.payment_type == payment_type)):
            raise HTTPException(status_code=409, detail=f"M-Pesa {payment_type} is already configured")
        label = "M-Pesa Paybill" if payment_type == "paybill" else "M-Pesa Till"
        instructions = payload.instructions.strip() if payload.instructions else (f"Pay via M-Pesa Paybill {number}. Use your {settings.app_name} order number as the account reference." if payment_type == "paybill" else f"Pay via M-Pesa Buy Goods and Services using Till Number {number}.")
        encrypted = encrypt_config({"payment_type": payment_type, "paybill_number": number if payment_type == "paybill" else "", "till_number": number if payment_type == "till" else "", "account_mode": account_mode, "account_reference": account_reference})
        method = PaymentMethod(public_id=secrets.token_hex(16), store_id=store.id, code=normalized_code, name=payload.name.strip() or label, is_enabled=payload.is_enabled, sort_order=20, instructions=instructions, config_encrypted=encrypted, payment_type=payment_type)
        db.add(method)
        await db.commit()
        return method_response(method)
    if normalized_code == "card":
        if await db.scalar(select(PaymentMethod.id).where(PaymentMethod.store_id == store.id, PaymentMethod.code == "card")):
            raise HTTPException(status_code=409, detail="Payment method already exists")
        method = PaymentMethod(public_id=secrets.token_hex(16), store_id=store.id, code="card", name=payload.name.strip(), is_enabled=payload.is_enabled, sort_order=30, instructions=payload.instructions.strip() if payload.instructions else "Accept card payments using your card terminal or configured card processor.", payment_type="card")
        db.add(method)
        await db.commit()
        return method_response(method)
    method, callback_token, callback_url = await PaymentService(db).create_method(user, tenant_public_id, payload.code, payload.name, payload.instructions, payload.is_enabled, payload.config)
    return method_response(method, callback_url, callback_token, merchant=True)


@router.patch("/tenants/{tenant_public_id}/payment-methods/{method_public_id}", response_model=PaymentMethodResponse)
async def update_payment_method(tenant_public_id: str, method_public_id: str, payload: PaymentMethodUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> PaymentMethodResponse:
    store = await resolve_store(db, user, tenant_public_id, "payments.manage")
    method = await db.scalar(select(PaymentMethod).where(PaymentMethod.store_id == store.id, PaymentMethod.public_id == method_public_id))
    if method is None:
        raise HTTPException(status_code=404, detail="Payment method not found")
    if method.code == "mpesa_paybill":
        current = decrypt_config(method.config_encrypted)
        if payload.name is not None:
            method.name = payload.name.strip()
        if payload.instructions is not None:
            method.instructions = payload.instructions.strip() or None
        if payload.is_enabled is not None:
            method.is_enabled = payload.is_enabled
        if payload.config is not None:
            merged = {**current, **payload.config}
            merged.setdefault("payment_type", method.payment_type or "paybill")
            payment_type, number, account_mode, account_reference = _validate_mpesa_paybill_config(merged)
            existing = await db.scalar(select(PaymentMethod.id).where(PaymentMethod.store_id == store.id, PaymentMethod.code == "mpesa_paybill", PaymentMethod.payment_type == payment_type, PaymentMethod.id != method.id))
            if existing is not None:
                raise HTTPException(status_code=409, detail=f"M-Pesa {payment_type} is already configured")
            merged.update({"payment_type": payment_type, "paybill_number": number if payment_type == "paybill" else "", "till_number": number if payment_type == "till" else "", "account_mode": account_mode, "account_reference": account_reference})
            method.config_encrypted = encrypt_config(merged)
            method.payment_type = payment_type
        await db.commit()
        return method_response(method)
    method, callback_url = await PaymentService(db).update_method(user, tenant_public_id, method_public_id, payload.name, payload.instructions, payload.is_enabled, payload.config)
    return method_response(method, callback_url, None, merchant=True)


@router.post("/tenants/{tenant_public_id}/payment-methods/{method_public_id}/test", response_model=dict[str, str])
async def test_payment_method(tenant_public_id: str, method_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    store = await resolve_store(db, user, tenant_public_id, "payments.manage")
    method = await db.scalar(select(PaymentMethod).where(PaymentMethod.store_id == store.id, PaymentMethod.public_id == method_public_id))
    if method is None or method.store_id != store.id:
        raise HTTPException(status_code=404, detail="Payment method not found")
    if method.code != "mpesa":
        raise HTTPException(status_code=422, detail="Only Daraja M-Pesa can be connection-tested")
    config = decrypt_config(method.config_encrypted)
    callback_token = config.get("callback_token")
    if not callback_token:
        raise HTTPException(status_code=503, detail="M-Pesa callback is not configured")
    callback_url = PaymentService._callback_url(callback_token)
    try:
        cleaned = validate_daraja_config(config, callback_url=callback_url)
        await MpesaClient(cleaned, callback_url)._access_token()
    except (MpesaProviderError, HTTPException) as exc:
        detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
        raise HTTPException(status_code=502, detail=f"M-Pesa connection failed: {detail}") from exc
    return {"status": "ok", "message": f"M-Pesa Daraja {cleaned.get('environment', 'sandbox')} connection is working."}


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
        raise HTTPException(status_code=422, detail="Only manual cash, M-Pesa Paybill/Till or card payments can be marked paid")
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
