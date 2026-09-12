from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.modules.auth.models.identity import User
from app.modules.catalogue.models.store import Store
from app.modules.catalogue.services.context import resolve_store
from app.modules.commerce.models.order import Order
from app.modules.commerce.models.order_status import OrderStatus
from app.modules.commerce.models.order_status_history import OrderStatusHistory
from app.modules.commerce.models.order_status_transition import OrderStatusTransition
from app.modules.commerce.models.payment import Payment
from app.modules.commerce.models.payment_attempt import PaymentAttempt
from app.modules.commerce.models.payment_event import PaymentEvent
from app.modules.commerce.models.payment_method import PaymentMethod
from app.modules.commerce.mpesa import MpesaClient, MpesaProviderError, mpesa_msisdn, validate_daraja_config
from app.modules.commerce.notifications import normalize_phone, queue_order_sms
from app.modules.commerce.payment_security import callback_token_hash, decrypt_config, encrypt_config, new_callback_token


def payment_response(payment: Payment) -> dict[str, object]:
    config = decrypt_config(payment.payment_method.config_encrypted) if payment.payment_method.config_encrypted else {}
    payment_type = config.get("payment_type")
    if payment.payment_method.code == "mpesa" and not payment_type:
        payment_type = "stk_push"
    elif payment.payment_method.code == "mpesa_paybill" and not payment_type:
        payment_type = "paybill"
    method = {
        "public_id": payment.payment_method.public_id,
        "code": "mpesa" if payment.payment_method.code == "mpesa_paybill" else payment.payment_method.code,
        "name": payment.payment_method.name,
        "is_enabled": payment.payment_method.is_enabled,
        "payment_type": str(payment_type) if payment_type else None,
        "instructions": payment.payment_method.instructions,
    }
    return {"public_id": payment.public_id, "status": payment.status, "amount_minor": payment.amount_minor, "currency": payment.currency, "method": method, "failure_reason": payment.failure_reason, "paid_at": payment.paid_at.isoformat() if payment.paid_at else None, "provider_reference": payment.provider_reference}


def payment_list_response(payment: Payment) -> dict[str, object]:
    return {**payment_response(payment), "order_public_id": payment.order.public_id, "order_number": payment.order.order_number, "customer_first_name": payment.order.customer_first_name, "customer_last_name": payment.order.customer_last_name, "customer_phone": payment.order.customer_phone, "attempt_count": len(payment.attempts), "created_at": payment.created_at.isoformat()}


class PaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_public_methods(self, store: Store) -> list[PaymentMethod]:
        return list((await self.db.scalars(select(PaymentMethod).where(PaymentMethod.store_id == store.id, PaymentMethod.is_enabled.is_(True)).order_by(PaymentMethod.sort_order, PaymentMethod.id))).all())

    async def list_methods(self, user: User, tenant_public_id: str) -> list[PaymentMethod]:
        store = await resolve_store(self.db, user, tenant_public_id, "payments.read")
        return list((await self.db.scalars(select(PaymentMethod).where(PaymentMethod.store_id == store.id).order_by(PaymentMethod.sort_order, PaymentMethod.id))).all())

    async def prepare_order_payment(self, store: Store, order: Order, method_public_id: str | None) -> Payment:
        method = await self._select_method(store.id, method_public_id)
        phone = normalize_phone(order.customer_phone or "")
        if not phone:
            raise HTTPException(status_code=422, detail="Customer phone is required for payment")
        if order.total_minor < 100:
            raise HTTPException(status_code=422, detail="Order total must be at least 1 KES")
        payment = Payment(
            public_id=secrets.token_hex(16),
            store_id=store.id,
            order_id=order.id,
            payment_method_id=method.id,
            status="pending",
            amount_minor=order.total_minor,
            currency=order.currency,
            customer_phone=phone,
        )
        payment.payment_method = method
        self.db.add(payment)
        await self.db.flush()
        return payment

    async def initiate(self, payment_public_id: str) -> Payment:
        payment = await self._load_payment(payment_public_id)
        if payment is None:
            raise HTTPException(status_code=404, detail="Payment not found")
        if payment.status in {"paid", "refunded", "partially_refunded"}:
            return payment
        if payment.payment_method.code in {"cash", "card"}:
            return payment
        if payment.payment_method.code != "mpesa":
            raise HTTPException(status_code=422, detail="This payment method is not supported yet")
        raw_config = decrypt_config(payment.payment_method.config_encrypted)
        callback_token = raw_config.get("callback_token")
        if not callback_token or not payment.payment_method.callback_token_hash:
            raise HTTPException(status_code=503, detail="M-Pesa callback is not configured")
        if callback_token_hash(callback_token) != payment.payment_method.callback_token_hash:
            raise HTTPException(status_code=503, detail="M-Pesa callback token is invalid")
        callback_url = self._callback_url(callback_token)
        config = validate_daraja_config(raw_config, callback_url=callback_url)
        client = MpesaClient(config, callback_url)
        try:
            phone = mpesa_msisdn(payment.customer_phone)
        except HTTPException:
            raise
        payment.customer_phone = normalize_phone(payment.customer_phone)
        attempt_number = (await self.db.scalar(select(PaymentAttempt.attempt_number).where(PaymentAttempt.payment_id == payment.id).order_by(PaymentAttempt.attempt_number.desc()).limit(1)) or 0) + 1
        attempt = PaymentAttempt(public_id=secrets.token_hex(16), payment_id=payment.id, attempt_number=attempt_number, status="processing", phone=payment.customer_phone, amount_minor=payment.amount_minor)
        self.db.add(attempt)
        payment.status = "processing"
        payment.failure_reason = None
        await self.db.commit()
        try:
            order_number = getattr(payment.order, "order_number", None) if payment.order is not None else None
            account_reference = str(order_number or config.get("account_reference") or "DukaMe").strip()[:12]
            result = await client.stk_push(payment.amount_minor, phone, account_reference)
        except (MpesaProviderError, HTTPException) as exc:
            payment = await self._load_payment(payment.public_id)
            if payment is None:
                raise HTTPException(status_code=500, detail="Payment state could not be recovered") from exc
            attempt = await self.db.scalar(select(PaymentAttempt).where(PaymentAttempt.payment_id == payment.id, PaymentAttempt.attempt_number == attempt_number))
            message = str(exc.detail if isinstance(exc, HTTPException) else exc)[:1000]
            if attempt:
                attempt.status = "failed"
                attempt.provider_response_message = message
            payment.status = "failed"
            payment.failure_reason = message
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

    async def retry(self, user: User, tenant_public_id: str, payment_public_id: str) -> Payment:
        store = await resolve_store(self.db, user, tenant_public_id, "payments.manage")
        payment = await self._load_payment(payment_public_id)
        if payment is None or payment.store_id != store.id:
            raise HTTPException(status_code=404, detail="Payment not found")
        if payment.payment_method.code != "mpesa":
            raise HTTPException(status_code=422, detail="Only M-Pesa payments can be retried")
        if payment.status != "failed":
            raise HTTPException(status_code=409, detail="Only failed payments can be retried")
        return await self.initiate(payment.public_id)

    async def create_method(self, user: User, tenant_public_id: str, code: str, name: str, instructions: str | None, enabled: bool, config: dict[str, str] | None) -> tuple[PaymentMethod, str | None, str | None]:
        store = await resolve_store(self.db, user, tenant_public_id, "payments.manage")
        normalized_code = code.strip().lower()
        if normalized_code not in {"cash", "mpesa", "card"}:
            raise HTTPException(status_code=422, detail="Unsupported payment method")
        if await self.db.scalar(select(PaymentMethod.id).where(PaymentMethod.store_id == store.id, PaymentMethod.code == normalized_code)):
            raise HTTPException(status_code=409, detail="Payment method already exists")
        callback_url = None
        callback_token = None
        encrypted = None
        callback_hash = None
        if normalized_code == "mpesa":
            cleaned = self._validate_mpesa_config(config)
            callback_token, callback_hash = new_callback_token()
            callback_url = self._callback_url(callback_token)
            validate_daraja_config(cleaned, callback_url=callback_url)
            encrypted = encrypt_config({**cleaned, "callback_token": callback_token})
        default_instructions = "Accept card payments using your card terminal or configured card processor." if normalized_code == "card" else instructions
        sort_order = {"cash": 10, "mpesa": 20, "card": 30}[normalized_code]
        method = PaymentMethod(public_id=secrets.token_hex(16), store_id=store.id, code=normalized_code, name=name.strip(), is_enabled=enabled, sort_order=sort_order, instructions=default_instructions.strip() if default_instructions else None, config_encrypted=encrypted, callback_token_hash=callback_hash)
        self.db.add(method)
        await self.db.commit()
        return method, callback_token, callback_url

    async def update_method(self, user: User, tenant_public_id: str, method_public_id: str, name: str | None, instructions: str | None, enabled: bool | None, config: dict[str, str] | None) -> tuple[PaymentMethod, str | None]:
        store = await resolve_store(self.db, user, tenant_public_id, "payments.manage")
        method = await self.db.scalar(select(PaymentMethod).where(PaymentMethod.store_id == store.id, PaymentMethod.public_id == method_public_id))
        if method is None:
            raise HTTPException(status_code=404, detail="Payment method not found")
        if name is not None:
            method.name = name.strip()
        if instructions is not None:
            method.instructions = instructions.strip() or None
        if enabled is not None:
            method.is_enabled = enabled
        callback_url = None
        if method.code == "mpesa":
            current = decrypt_config(method.config_encrypted)
            if config is not None:
                incoming = {k: v for k, v in config.items() if k != "callback_token"}
                merged = {**current, **incoming}
                cleaned = self._validate_mpesa_config(merged)
                if current.get("callback_token"):
                    cleaned["callback_token"] = current["callback_token"]
                current = cleaned
                method.config_encrypted = encrypt_config(current)
            callback_token = current.get("callback_token")
            if not callback_token:
                callback_token, callback_hash = new_callback_token()
                current["callback_token"] = callback_token
                method.callback_token_hash = callback_hash
                method.config_encrypted = encrypt_config(current)
            callback_url = self._callback_url(callback_token)
        await self.db.commit()
        return method, callback_url

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
        await self._confirm_order_after_payment(payment)
        await self.db.commit()
        return await self._load_payment(payment.public_id)

    async def callback(self, callback_token: str, payload: dict) -> None:
        """Idempotent STK callback. Unknown attempts return quietly to avoid Safaricom retry storms."""
        if not callback_token or len(callback_token) < 16:
            raise HTTPException(status_code=404, detail="Callback not found")
        method = await self.db.scalar(
            select(PaymentMethod).where(
                PaymentMethod.code == "mpesa",
                PaymentMethod.callback_token_hash == callback_token_hash(callback_token),
            )
        )
        if method is None:
            raise HTTPException(status_code=404, detail="Callback not found")
        body = payload.get("Body") if isinstance(payload, dict) else None
        callback = body.get("stkCallback", {}) if isinstance(body, dict) else {}
        if not isinstance(callback, dict):
            raise HTTPException(status_code=400, detail="Invalid payment callback")
        checkout_request_id = str(callback.get("CheckoutRequestID") or "").strip()
        if not checkout_request_id:
            raise HTTPException(status_code=400, detail="Invalid payment callback")
        attempt = await self.db.scalar(
            select(PaymentAttempt)
            .options(selectinload(PaymentAttempt.payment).selectinload(Payment.payment_method), selectinload(PaymentAttempt.payment).selectinload(Payment.order))
            .where(PaymentAttempt.provider_checkout_request_id == checkout_request_id)
        )
        if attempt is None or attempt.payment is None:
            return
        if attempt.payment.payment_method_id != method.id or attempt.payment.store_id != method.store_id:
            return
        if attempt.payment.status == "paid":
            result_code = str(callback.get("ResultCode", ""))
            event_key = f"mpesa:stk:{checkout_request_id}:{result_code}:paid-noop"
            if not await self.db.scalar(select(PaymentEvent.id).where(PaymentEvent.event_key == event_key)):
                payload_hash = hashlib.sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True, default=str).encode()).hexdigest()
                self.db.add(
                    PaymentEvent(
                        public_id=secrets.token_hex(16),
                        payment_id=attempt.payment.id,
                        event_key=event_key,
                        event_type="mpesa.stk.callback.duplicate",
                        payload_hash=payload_hash,
                        processed_at=datetime.now(UTC),
                    )
                )
                await self.db.commit()
            return
        result_code = str(callback.get("ResultCode", ""))
        payload_hash = hashlib.sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True, default=str).encode()).hexdigest()
        event_key = f"mpesa:stk:{checkout_request_id}:{result_code}"
        if await self.db.scalar(select(PaymentEvent.id).where(PaymentEvent.event_key == event_key)):
            return
        self.db.add(
            PaymentEvent(
                public_id=secrets.token_hex(16),
                payment_id=attempt.payment.id,
                event_key=event_key,
                event_type="mpesa.stk.callback",
                payload_hash=payload_hash,
                processed_at=datetime.now(UTC),
            )
        )
        if result_code == "0":
            items = callback.get("CallbackMetadata", {}).get("Item", []) if isinstance(callback.get("CallbackMetadata"), dict) else []
            metadata = {str(item.get("Name")): item.get("Value") for item in items if isinstance(item, dict) and item.get("Name")}
            amount = self._amount_from_provider(metadata.get("Amount"))
            receipt = str(metadata.get("MpesaReceiptNumber") or "").strip()
            phone = str(metadata.get("PhoneNumber") or "").strip()
            if not receipt or amount is None or amount != attempt.payment.amount_minor:
                attempt.status = "failed"
                attempt.provider_response_code = result_code
                attempt.provider_response_message = "Payment callback amount or receipt could not be verified"
                if attempt.payment.status not in {"paid", "refunded", "partially_refunded"}:
                    attempt.payment.status = "failed"
                    attempt.payment.failure_reason = "Payment callback could not be verified"
            else:
                attempt.status = "succeeded"
                attempt.provider_response_code = result_code
                attempt.provider_response_message = str(callback.get("ResultDesc") or "Payment received")[:1000]
                attempt.payment.status = "paid"
                attempt.payment.paid_at = datetime.now(UTC)
                attempt.payment.provider_reference = receipt[:128]
                attempt.payment.provider_status_code = result_code
                attempt.payment.failure_reason = None
                if phone:
                    try:
                        attempt.payment.customer_phone = normalize_phone(phone if phone.startswith("+") or phone.startswith("0") else f"+{phone}")
                    except Exception:
                        attempt.payment.customer_phone = phone[:32]
                await self._confirm_order_after_payment(attempt.payment)
        else:
            attempt.status = "failed"
            attempt.provider_response_code = result_code
            attempt.provider_response_message = str(callback.get("ResultDesc") or "Payment was not completed")[:1000]
            if attempt.payment.status not in {"paid", "refunded", "partially_refunded"}:
                attempt.payment.status = "failed"
                attempt.payment.provider_status_code = result_code
                attempt.payment.failure_reason = attempt.provider_response_message
        await self.db.commit()

    async def list_payments(self, user: User, tenant_public_id: str, offset: int, limit: int, status: str | None) -> list[Payment]:
        store = await resolve_store(self.db, user, tenant_public_id, "payments.read")
        stmt = select(Payment).options(selectinload(Payment.payment_method), selectinload(Payment.attempts), selectinload(Payment.order)).where(Payment.store_id == store.id).order_by(Payment.created_at.desc(), Payment.id.desc()).offset(offset).limit(limit)
        if status:
            stmt = stmt.where(Payment.status == status.strip().lower())
        return list((await self.db.scalars(stmt)).all())

    async def get_payment(self, user: User, tenant_public_id: str, payment_public_id: str) -> Payment:
        store = await resolve_store(self.db, user, tenant_public_id, "payments.read")
        payment = await self._load_payment(payment_public_id)
        if payment is None or payment.store_id != store.id:
            raise HTTPException(status_code=404, detail="Payment not found")
        return payment

    async def get_order_payment(self, store: Store, order_public_id: str) -> Payment | None:
        return await self.db.scalar(select(Payment).join(Order, Payment.order_id == Order.id).options(selectinload(Payment.payment_method)).where(Payment.store_id == store.id, Order.public_id == order_public_id))

    async def _confirm_order_after_payment(self, payment: Payment) -> None:
        order = await self.db.scalar(select(Order).options(selectinload(Order.status)).where(Order.id == payment.order_id).with_for_update())
        if order is None or order.status.is_terminal or order.status.code != "pending":
            return
        confirmed = await self.db.scalar(select(OrderStatus).where(OrderStatus.code == "confirmed", OrderStatus.is_active.is_(True)))
        if confirmed is None:
            return
        transition = await self.db.scalar(select(OrderStatusTransition).where(OrderStatusTransition.from_status_id == order.status_id, OrderStatusTransition.to_status_id == confirmed.id))
        if transition is None:
            return
        order.status_id = confirmed.id
        self.db.add(OrderStatusHistory(order_id=order.id, status_id=confirmed.id, source="payment"))
        store = await self.db.scalar(select(Store).where(Store.id == payment.store_id))
        if store:
            await queue_order_sms(self.db, order, confirmed, store.name, store.slug)

    @staticmethod
    def _amount_from_provider(value: object) -> int | None:
        if value is None:
            return None
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
        if amount < 0 or amount.as_tuple().exponent < -2:
            return None
        return int(amount * 100)

    @staticmethod
    def _validate_mpesa_config(config: dict[str, str] | None) -> dict[str, str]:
        if config is None:
            raise HTTPException(status_code=422, detail="M-Pesa configuration is required")
        coerced = {str(k): ("" if v is None else str(v)) for k, v in config.items()}
        return validate_daraja_config(coerced)

    @staticmethod
    def _callback_url(callback_token: str) -> str:
        return f"{settings.public_api_base_url.rstrip('/')}/api/v1/payments/mpesa/callback/{callback_token}"

    async def _select_method(self, store_id: int, public_id: str | None) -> PaymentMethod:
        if public_id:
            method = await self.db.scalar(select(PaymentMethod).where(PaymentMethod.store_id == store_id, PaymentMethod.public_id == public_id, PaymentMethod.is_enabled.is_(True)))
        else:
            method = await self.db.scalar(select(PaymentMethod).where(PaymentMethod.store_id == store_id, PaymentMethod.code == "cash", PaymentMethod.is_enabled.is_(True)))
        if method is None:
            raise HTTPException(status_code=422, detail="Selected payment method is not available")
        return method

    async def _load_payment(self, public_id: str) -> Payment | None:
        return await self.db.scalar(select(Payment).options(selectinload(Payment.payment_method), selectinload(Payment.attempts), selectinload(Payment.events), selectinload(Payment.order).selectinload(Order.status)).where(Payment.public_id == public_id))
