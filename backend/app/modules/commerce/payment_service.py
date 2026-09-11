from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.modules.auth.models.identity import User
from app.modules.catalogue.models.store import Store
from app.modules.catalogue.services.context import resolve_store
from app.modules.commerce.models.order import Order
from app.modules.commerce.models.payment import Payment
from app.modules.commerce.models.payment_attempt import PaymentAttempt
from app.modules.commerce.models.payment_event import PaymentEvent
from app.modules.commerce.models.payment_method import PaymentMethod
from app.modules.commerce.mpesa import MpesaClient, MpesaProviderError
from app.modules.commerce.payment_security import callback_token_hash, decrypt_config, encrypt_config, new_callback_token

PAYMENT_STATUSES = {"pending", "processing", "paid", "failed", "cancelled", "refunded", "partially_refunded"}


def payment_response(payment: Payment) -> dict[str, object]:
    return {
        "public_id": payment.public_id,
        "status": payment.status,
        "amount_minor": payment.amount_minor,
        "currency": payment.currency,
        "method": {"public_id": payment.payment_method.public_id, "code": payment.payment_method.code, "name": payment.payment_method.name},
        "failure_reason": payment.failure_reason,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
        "provider_reference": payment.provider_reference,
    }


class PaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_public_methods(self, store: Store) -> list[PaymentMethod]:
        return list((await self.db.scalars(select(PaymentMethod).where(PaymentMethod.store_id == store.id, PaymentMethod.is_enabled.is_(True)).order_by(PaymentMethod.sort_order, PaymentMethod.id))).all())

    async def prepare_order_payment(self, store: Store, order: Order, method_public_id: str | None) -> Payment:
        method = await self._select_method(store.id, method_public_id)
        payment = Payment(public_id=secrets.token_hex(16), store_id=store.id, order_id=order.id, payment_method_id=method.id, status="pending", amount_minor=order.total_minor, currency=order.currency, customer_phone=order.customer_phone)
        self.db.add(payment)
        await self.db.flush()
        return payment

    async def initiate(self, payment_public_id: str) -> Payment:
        payment = await self._load_payment(payment_public_id)
        if payment is None:
            raise HTTPException(status_code=404, detail="Payment not found")
        if payment.status in {"paid", "refunded", "partially_refunded"}:
            return payment
        if payment.payment_method.code == "cash":
            return payment
        if payment.payment_method.code != "mpesa":
            raise HTTPException(status_code=422, detail="This payment method is not supported yet")
        config = decrypt_config(payment.payment_method.config_encrypted)
        callback_hash = payment.payment_method.callback_token_hash
        if not callback_hash:
            raise HTTPException(status_code=503, detail="M-Pesa callback is not configured")
        callback_url = f"{settings.public_api_base_url.rstrip('/')}/api/v1/payments/mpesa/callback/{callback_hash}"
        client = MpesaClient(config, callback_url)
        attempt_number = (await self.db.scalar(select(PaymentAttempt.attempt_number).where(PaymentAttempt.payment_id == payment.id).order_by(PaymentAttempt.attempt_number.desc()).limit(1)) or 0) + 1
        attempt = PaymentAttempt(public_id=secrets.token_hex(16), payment_id=payment.id, attempt_number=attempt_number, status="processing", phone=payment.customer_phone, amount_minor=payment.amount_minor)
        self.db.add(attempt)
        payment.status = "processing"
        await self.db.commit()
        try:
            result = await client.stk_push(payment.amount_minor, payment.customer_phone, f"Order {payment.order_id}")
        except (MpesaProviderError, HTTPException) as exc:
            payment = await self._load_payment(payment.public_id)
            if payment is None:
                raise HTTPException(status_code=500, detail="Payment state could not be recovered") from exc
            attempt = await self.db.scalar(select(PaymentAttempt).where(PaymentAttempt.payment_id == payment.id, PaymentAttempt.attempt_number == attempt_number))
            if attempt:
                attempt.status = "failed"
                attempt.provider_response_message = str(exc.detail if isinstance(exc, HTTPException) else exc)[:1000]
            payment.status = "failed"
            payment.failure_reason = str(exc.detail if isinstance(exc, HTTPException) else exc)[:1000]
            await self.db.commit()
            raise
        attempt = await self.db.scalar(select(PaymentAttempt).where(PaymentAttempt.payment_id == payment.id, PaymentAttempt.attempt_number == attempt_number))
        if attempt:
            attempt.status = "awaiting_customer"
            attempt.provider_request_id = result.get("merchant_request_id")
            attempt.provider_checkout_request_id = result.get("checkout_request_id")
            attempt.provider_response_code = result.get("response_code")
            attempt.provider_response_message = result.get("response_message")
        payment.provider_reference = result.get("checkout_request_id")
        payment.provider_status_code = result.get("response_code")
        await self.db.commit()
        return await self._load_payment(payment.public_id)

    async def create_method(self, user: User, tenant_public_id: str, code: str, name: str, instructions: str | None, enabled: bool, config: dict[str, str] | None) -> tuple[PaymentMethod, str | None, str | None]:
        store = await resolve_store(self.db, user, tenant_public_id, "payments.manage")
        normalized_code = code.strip().lower()
        if normalized_code not in {"cash", "mpesa"}:
            raise HTTPException(status_code=422, detail="Unsupported payment method")
        if await self.db.scalar(select(PaymentMethod.id).where(PaymentMethod.store_id == store.id, PaymentMethod.code == normalized_code)):
            raise HTTPException(status_code=409, detail="Payment method already exists")
        callback_url = None
        callback_token = None
        encrypted = None
        if normalized_code == "mpesa":
            if not config:
                raise HTTPException(status_code=422, detail="M-Pesa configuration is required")
            callback_token, callback_hash = new_callback_token()
            encrypted = encrypt_config(config)
            callback_url = f"{settings.public_api_base_url.rstrip('/')}/api/v1/payments/mpesa/callback/{callback_token}"
        else:
            callback_hash = None
        method = PaymentMethod(public_id=secrets.token_hex(16), store_id=store.id, code=normalized_code, name=name.strip(), is_enabled=enabled, sort_order=20, instructions=instructions.strip() if instructions else None, config_encrypted=encrypted, callback_token_hash=callback_hash)
        self.db.add(method)
        await self.db.commit()
        return method, callback_token, callback_url

    async def set_cash_paid(self, user: User, tenant_public_id: str, payment_public_id: str) -> Payment:
        store = await resolve_store(self.db, user, tenant_public_id, "payments.manage")
        payment = await self._load_payment(payment_public_id)
        if payment is None or payment.store_id != store.id:
            raise HTTPException(status_code=404, detail="Payment not found")
        if payment.payment_method.code != "cash":
            raise HTTPException(status_code=422, detail="Only cash payments can be manually marked paid")
        if payment.status == "paid":
            return payment
        if payment.status in {"refunded", "partially_refunded", "cancelled"}:
            raise HTTPException(status_code=409, detail="Payment cannot be marked paid")
        payment.status = "paid"
        payment.paid_at = datetime.now(UTC)
        payment.failure_reason = None
        await self.db.commit()
        return await self._load_payment(payment.public_id)

    async def callback(self, callback_token: str, payload: dict) -> None:
        method = await self.db.scalar(select(PaymentMethod).where(PaymentMethod.code == "mpesa", PaymentMethod.callback_token_hash == callback_token_hash(callback_token)))
        if method is None:
            raise HTTPException(status_code=404, detail="Callback not found")
        callback = payload.get("Body", {}).get("stkCallback", {})
        checkout_request_id = str(callback.get("CheckoutRequestID") or "")
        if not checkout_request_id:
            raise HTTPException(status_code=400, detail="Invalid payment callback")
        attempt = await self.db.scalar(select(PaymentAttempt).options(selectinload(PaymentAttempt.payment).selectinload(Payment.payment_method)).where(PaymentAttempt.provider_checkout_request_id == checkout_request_id))
        if attempt is None or attempt.payment.payment_method_id != method.id:
            raise HTTPException(status_code=404, detail="Payment attempt not found")
        result_code = str(callback.get("ResultCode", ""))
        payload_hash = hashlib.sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
        event_key = f"mpesa:stk:{checkout_request_id}:{result_code}"
        if await self.db.scalar(select(PaymentEvent.id).where(PaymentEvent.event_key == event_key)):
            return
        event = PaymentEvent(public_id=secrets.token_hex(16), payment_id=attempt.payment.id, event_key=event_key, event_type="mpesa.stk.callback", payload_hash=payload_hash, processed_at=datetime.now(UTC))
        self.db.add(event)
        if result_code == "0":
            metadata = {str(item.get("Name")): item.get("Value") for item in callback.get("CallbackMetadata", {}).get("Item", []) if item.get("Name")}
            amount = metadata.get("Amount")
            receipt = str(metadata.get("MpesaReceiptNumber") or "")
            phone = str(metadata.get("PhoneNumber") or "")
            if not receipt or amount is None or int(round(float(amount) * 100)) != attempt.payment.amount_minor:
                attempt.status = "failed"
                attempt.provider_response_code = result_code
                attempt.provider_response_message = "Payment callback amount or receipt could not be verified"
                attempt.payment.status = "failed"
                attempt.payment.failure_reason = "Payment callback could not be verified"
            else:
                attempt.status = "succeeded"
                attempt.provider_response_code = result_code
                attempt.provider_response_message = str(callback.get("ResultDesc") or "Payment received")[:1000]
                attempt.payment.status = "paid"
                attempt.payment.paid_at = datetime.now(UTC)
                attempt.payment.provider_reference = receipt
                attempt.payment.provider_status_code = result_code
                attempt.payment.failure_reason = None
                if phone:
                    attempt.payment.customer_phone = phone
        else:
            attempt.status = "failed"
            attempt.provider_response_code = result_code
            attempt.provider_response_message = str(callback.get("ResultDesc") or "Payment was not completed")[:1000]
            attempt.payment.status = "failed"
            attempt.payment.provider_status_code = result_code
            attempt.payment.failure_reason = attempt.provider_response_message
        await self.db.commit()

    async def get_order_payment(self, store: Store, order_public_id: str) -> Payment | None:
        return await self.db.scalar(select(Payment).join(Order, Payment.order_id == Order.id).options(selectinload(Payment.payment_method)).where(Payment.store_id == store.id, Order.public_id == order_public_id))

    async def _select_method(self, store_id: int, public_id: str | None) -> PaymentMethod:
        if public_id:
            method = await self.db.scalar(select(PaymentMethod).where(PaymentMethod.store_id == store_id, PaymentMethod.public_id == public_id, PaymentMethod.is_enabled.is_(True)))
        else:
            method = await self.db.scalar(select(PaymentMethod).where(PaymentMethod.store_id == store_id, PaymentMethod.code == "cash", PaymentMethod.is_enabled.is_(True)))
        if method is None:
            raise HTTPException(status_code=422, detail="Selected payment method is not available")
        return method

    async def _load_payment(self, public_id: str) -> Payment | None:
        return await self.db.scalar(select(Payment).options(selectinload(Payment.payment_method), selectinload(Payment.attempts)).where(Payment.public_id == public_id))
