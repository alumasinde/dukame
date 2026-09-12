from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.time import ensure_utc, utc_now
from app.modules.auth.models.identity import User
from app.modules.subscriptions.models.billing import SubscriptionInvoice, SubscriptionPayment
from app.modules.subscriptions.models.subscription import Plan, Subscription
from app.modules.subscriptions.services.subscription import (
    STATUS_ACTIVE,
    STATUS_CANCELLED,
    STATUS_EXPIRED,
    STATUS_PAST_DUE,
    STATUS_TRIAL,
    VALID_INTERVALS,
    _add_event,
    _assert_transition,
    get_plan_by_public_id,
    get_tenant_subscription,
    interval_end,
)

logger = logging.getLogger(__name__)

INVOICE_OPEN = "open"
INVOICE_PAID = "paid"
INVOICE_VOID = "void"
INVOICE_UNCOLLECTIBLE = "uncollectible"

PAYMENT_PENDING = "pending"
PAYMENT_SUCCEEDED = "succeeded"
PAYMENT_FAILED = "failed"
PAYMENT_CANCELLED = "cancelled"

PURPOSE_UPGRADE = "upgrade"
PURPOSE_RENEWAL = "renewal"
PURPOSE_REACTIVATION = "reactivation"


def _idempotency_key(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


def prorate_upgrade_amount(
    subscription: Subscription,
    new_plan: Plan,
    billing_interval: str,
    *,
    now: datetime | None = None,
) -> tuple[int, dict[str, Any]]:
    """Compute payable amount for an upgrade with simple time-based credit.

    Credit = unused fraction of the current paid period's price.
    Never credits above the new plan price; minimum charge is 0.
    """
    full = new_plan.price_for_interval(billing_interval)
    meta: dict[str, Any] = {
        "list_price_minor": full,
        "credit_minor": 0,
        "prorated": False,
    }
    if full <= 0:
        return 0, meta

    current_plan = subscription.plan
    if current_plan is None or current_plan.is_free:
        return full, meta

    try:
        old_price = current_plan.price_for_interval(subscription.billing_interval)
    except ValueError:
        return full, meta
    if old_price <= 0:
        return full, meta

    ts = now or utc_now()
    period_end = subscription.current_period_end
    period_start = subscription.starts_at
    if period_end is None or period_start is None:
        return full, meta
    period_end = ensure_utc(period_end)
    period_start = ensure_utc(period_start)
    if period_end <= ts:
        return full, meta

    total_seconds = (period_end - period_start).total_seconds()
    remaining_seconds = max((period_end - ts).total_seconds(), 0.0)
    if total_seconds <= 0:
        return full, meta

    credit = int(old_price * (remaining_seconds / total_seconds))
    credit = max(min(credit, full), 0)
    payable = max(full - credit, 0)
    meta.update(
        {
            "credit_minor": credit,
            "prorated": credit > 0,
            "remaining_ratio": round(remaining_seconds / total_seconds, 6),
            "from_plan_price_minor": old_price,
            "from_interval": subscription.billing_interval,
        }
    )
    return payable, meta

async def list_tenant_invoices(
    db: AsyncSession, tenant_id: int, *, limit: int = 50
) -> list[SubscriptionInvoice]:
    result = await db.execute(
        select(SubscriptionInvoice)
        .options(selectinload(SubscriptionInvoice.payments))
        .where(SubscriptionInvoice.tenant_id == tenant_id)
        .order_by(SubscriptionInvoice.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().unique().all())


async def get_invoice_by_public_id(
    db: AsyncSession, public_id: str
) -> SubscriptionInvoice | None:
    result = await db.execute(
        select(SubscriptionInvoice)
        .options(selectinload(SubscriptionInvoice.payments))
        .where(SubscriptionInvoice.public_id == public_id)
    )
    return result.scalar_one_or_none()


async def _create_invoice(
    db: AsyncSession,
    *,
    tenant_id: int,
    subscription: Subscription,
    plan: Plan,
    billing_interval: str,
    purpose: str,
    amount_minor: int,
    period_start,
    period_end,
    idempotency_key: str | None,
    metadata: dict[str, Any] | None = None,
) -> SubscriptionInvoice:
    if idempotency_key:
        existing = await db.scalar(
            select(SubscriptionInvoice).where(
                SubscriptionInvoice.idempotency_key == idempotency_key
            )
        )
        if existing is not None:
            return existing

    now = utc_now()
    invoice = SubscriptionInvoice(
        public_id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        subscription_id=subscription.id,
        plan_id=plan.id,
        billing_interval=billing_interval,
        purpose=purpose,
        status=INVOICE_OPEN,
        currency=plan.currency,
        amount_minor=amount_minor,
        period_start=period_start,
        period_end=period_end,
        due_at=now + timedelta(days=settings.subscription_invoice_due_days),
        idempotency_key=idempotency_key,
        metadata_json=metadata or {},
    )
    db.add(invoice)
    await db.flush()
    return invoice


async def create_upgrade_invoice(
    db: AsyncSession,
    user: User,
    tenant_public_id: str,
    plan_public_id: str,
    billing_interval: str,
) -> tuple[Subscription, SubscriptionInvoice]:
    if billing_interval not in VALID_INTERVALS:
        raise HTTPException(status_code=422, detail="Invalid billing interval")

    subscription = await get_tenant_subscription(db, user, tenant_public_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    if subscription.status in {STATUS_CANCELLED, STATUS_EXPIRED}:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "subscription_not_modifiable",
                "status": subscription.status,
            },
        )

    plan = await get_plan_by_public_id(db, plan_public_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    list_price = plan.price_for_interval(billing_interval)
    if list_price <= 0:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "free_plan_use_change",
                "message": "Free plan changes use the change endpoint, not the payment flow",
            },
        )

    now = utc_now()
    amount, proration_meta = prorate_upgrade_amount(
        subscription, plan, billing_interval, now=now
    )
    period_end = interval_end(now, billing_interval, 0)
    key = _idempotency_key(
        "upgrade",
        str(subscription.id),
        plan.public_id,
        billing_interval,
        now.strftime("%Y%m%d%H"),
    )
    invoice = await _create_invoice(
        db,
        tenant_id=subscription.tenant_id,
        subscription=subscription,
        plan=plan,
        billing_interval=billing_interval,
        purpose=PURPOSE_UPGRADE,
        amount_minor=amount,
        period_start=now,
        period_end=period_end,
        idempotency_key=key,
        metadata={
            "from_plan": subscription.plan.slug,
            "to_plan": plan.slug,
            "actor_user_id": user.id,
            **proration_meta,
        },
    )

    # Zero after credit → apply immediately without payment provider.
    if amount == 0 and invoice.status == INVOICE_OPEN:
        await apply_paid_invoice(db, invoice)

    return subscription, invoice


async def initiate_invoice_payment(
    db: AsyncSession,
    invoice: SubscriptionInvoice,
    *,
    phone: str,
) -> SubscriptionPayment:
    if invoice.status != INVOICE_OPEN:
        raise HTTPException(
            status_code=409,
            detail={"code": "invoice_not_open", "status": invoice.status},
        )
    if invoice.amount_minor <= 0:
        raise HTTPException(status_code=422, detail="Invoice amount must be positive")

    payment = SubscriptionPayment(
        public_id=uuid.uuid4().hex,
        invoice_id=invoice.id,
        status=PAYMENT_PENDING,
        provider="mpesa",
        amount_minor=invoice.amount_minor,
        currency=invoice.currency,
        phone=phone,
    )
    db.add(payment)
    await db.flush()

    if not settings.platform_mpesa_enabled:
        logger.info(
            "platform_mpesa_disabled_invoice_left_open",
            extra={"invoice_public_id": invoice.public_id},
        )
        return payment

    try:
        from app.modules.commerce.mpesa import MpesaClient

        config = {
            "consumer_key": settings.platform_mpesa_consumer_key or "",
            "consumer_secret": (
                settings.platform_mpesa_consumer_secret.get_secret_value()
                if settings.platform_mpesa_consumer_secret
                else ""
            ),
            "shortcode": settings.platform_mpesa_shortcode or "",
            "passkey": (
                settings.platform_mpesa_passkey.get_secret_value()
                if settings.platform_mpesa_passkey
                else ""
            ),
            "environment": settings.platform_mpesa_environment,
            "transaction_type": settings.platform_mpesa_transaction_type,
            "account_reference": settings.platform_mpesa_account_reference[:12],
            "transaction_desc": settings.platform_mpesa_transaction_desc[:13],
        }
        callback_url = (
            f"{settings.public_api_base_url.rstrip('/')}"
            f"/api/v1/public/subscriptions/mpesa/callback"
        )
        client = MpesaClient(config, callback_url)
        result = await client.stk_push(
            amount_minor=invoice.amount_minor,
            phone=phone,
            account_reference=invoice.public_id[:12],
        )
        payment.provider_checkout_request_id = result.get("checkout_request_id")
        payment.provider_merchant_request_id = result.get("merchant_request_id")
        payment.provider_status_code = result.get("response_code")
        await db.flush()
    except Exception as exc:
        payment.status = PAYMENT_FAILED
        payment.failure_reason = str(exc)[:1000]
        await db.flush()
        logger.exception("subscription_stk_push_failed")
        raise HTTPException(
            status_code=502,
            detail={
                "code": "payment_provider_error",
                "message": "Could not initiate M-Pesa payment",
            },
        ) from exc

    return payment


async def apply_paid_invoice(db: AsyncSession, invoice: SubscriptionInvoice) -> Subscription:
    """Mark invoice paid and apply plan / period changes on the subscription."""
    if invoice.status == INVOICE_PAID:
        result = await db.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan).selectinload(Plan.features))
            .where(Subscription.id == invoice.subscription_id)
        )
        return result.scalar_one()

    if invoice.status != INVOICE_OPEN:
        raise HTTPException(
            status_code=409,
            detail={"code": "invoice_not_open", "status": invoice.status},
        )

    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan).selectinload(Plan.features))
        .where(Subscription.id == invoice.subscription_id)
        .with_for_update()
    )
    subscription = result.scalar_one()
    plan = await db.scalar(
        select(Plan).options(selectinload(Plan.features)).where(Plan.id == invoice.plan_id)
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    now = utc_now()
    old_status = subscription.status
    old_plan_slug = subscription.plan.slug if subscription.plan else None

    # Payment confirmation can revive terminal states.
    if old_status in {STATUS_CANCELLED, STATUS_EXPIRED}:
        subscription.status = STATUS_ACTIVE
    elif old_status in {STATUS_TRIAL, STATUS_ACTIVE, STATUS_PAST_DUE}:
        subscription.status = STATUS_ACTIVE
    else:
        _assert_transition(old_status, STATUS_ACTIVE)
        subscription.status = STATUS_ACTIVE

    subscription.plan_id = plan.id
    subscription.plan = plan
    subscription.billing_interval = invoice.billing_interval
    subscription.cancel_at_period_end = False
    subscription.cancelled_at = None
    subscription.starts_at = invoice.period_start or now
    subscription.current_period_end = invoice.period_end or interval_end(
        now, invoice.billing_interval, 0
    )

    invoice.status = INVOICE_PAID
    invoice.paid_at = now

    _add_event(
        db,
        subscription.id,
        "subscription.invoice_paid",
        {
            "invoice_public_id": invoice.public_id,
            "purpose": invoice.purpose,
            "from_plan": old_plan_slug,
            "to_plan": plan.slug,
            "from_status": old_status,
            "to_status": subscription.status,
            "amount_minor": invoice.amount_minor,
            "currency": invoice.currency,
        },
    )
    await db.flush()
    return subscription


async def mark_invoice_paid_manual(
    db: AsyncSession,
    *,
    invoice: SubscriptionInvoice,
    actor_user_id: int | None = None,
    note: str | None = None,
) -> Subscription:
    """Support / offline payment: mark open invoice paid and apply subscription."""
    if invoice.status != INVOICE_OPEN:
        raise HTTPException(
            status_code=409,
            detail={"code": "invoice_not_open", "status": invoice.status},
        )

    payment = SubscriptionPayment(
        public_id=uuid.uuid4().hex,
        invoice_id=invoice.id,
        status=PAYMENT_SUCCEEDED,
        provider="manual",
        amount_minor=invoice.amount_minor,
        currency=invoice.currency,
        paid_at=utc_now(),
        provider_reference=(note or "manual")[:128],
    )
    db.add(payment)
    await db.flush()

    subscription = await apply_paid_invoice(db, invoice)
    _add_event(
        db,
        subscription.id,
        "subscription.invoice_marked_paid",
        {
            "invoice_public_id": invoice.public_id,
            "actor_user_id": actor_user_id,
            "note": note,
            "source": "manual",
        },
    )
    await db.flush()
    return subscription


async def handle_mpesa_callback(db: AsyncSession, body: dict[str, Any]) -> dict[str, str]:
    callback = body.get("Body", {}).get("stkCallback", {}) if isinstance(body, dict) else {}
    checkout_id = callback.get("CheckoutRequestID")
    result_code = str(callback.get("ResultCode", ""))
    result_desc = str(callback.get("ResultDesc") or "")

    if not checkout_id:
        return {"ResultCode": "1", "ResultDesc": "Missing CheckoutRequestID"}

    payment = await db.scalar(
        select(SubscriptionPayment).where(
            SubscriptionPayment.provider_checkout_request_id == checkout_id
        )
    )
    if payment is None:
        logger.warning(
            "subscription_callback_unknown_checkout", extra={"checkout_id": checkout_id}
        )
        return {"ResultCode": "0", "ResultDesc": "Accepted"}

    invoice = await get_invoice_by_id_for_update(db, payment.invoice_id)
    if invoice is None:
        return {"ResultCode": "0", "ResultDesc": "Accepted"}

    payment.provider_status_code = result_code
    if result_code == "0":
        items = callback.get("CallbackMetadata", {}).get("Item", []) or []
        receipt = None
        for item in items:
            if item.get("Name") == "MpesaReceiptNumber":
                receipt = str(item.get("Value") or "") or None
        payment.status = PAYMENT_SUCCEEDED
        payment.provider_reference = receipt
        payment.paid_at = utc_now()
        payment.failure_reason = None
        await apply_paid_invoice(db, invoice)
    else:
        payment.status = PAYMENT_FAILED
        payment.failure_reason = result_desc[:1000]

    await db.flush()
    return {"ResultCode": "0", "ResultDesc": "Accepted"}


async def get_invoice_by_id_for_update(
    db: AsyncSession, invoice_id: int
) -> SubscriptionInvoice | None:
    result = await db.execute(
        select(SubscriptionInvoice)
        .options(selectinload(SubscriptionInvoice.payments))
        .where(SubscriptionInvoice.id == invoice_id)
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def create_renewal_invoices(db: AsyncSession, *, batch_size: int = 100) -> int:
    now = utc_now()
    window_end = now + timedelta(days=settings.subscription_renewal_lead_days)

    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(
            Subscription.status.in_([STATUS_ACTIVE, STATUS_TRIAL, STATUS_PAST_DUE]),
            Subscription.cancel_at_period_end.is_(False),
            Subscription.current_period_end.is_not(None),
            Subscription.current_period_end <= window_end,
            Subscription.current_period_end > now,
        )
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    subscriptions = list(result.scalars().unique().all())
    created = 0
    for sub in subscriptions:
        plan = sub.plan
        if plan is None:
            continue
        amount = plan.price_for_interval(sub.billing_interval)
        if amount <= 0:
            sub.current_period_end = interval_end(
                sub.current_period_end or now, sub.billing_interval, 0
            )
            sub.status = STATUS_ACTIVE
            _add_event(
                db,
                sub.id,
                "subscription.renewed_free",
                {"period_end": sub.current_period_end.isoformat()},
            )
            created += 1
            continue

        period_start = sub.current_period_end or now
        period_end = interval_end(period_start, sub.billing_interval, 0)
        key = _idempotency_key(
            "renewal",
            str(sub.id),
            plan.public_id,
            sub.billing_interval,
            period_start.strftime("%Y%m%d"),
        )
        existing = await db.scalar(
            select(SubscriptionInvoice.id).where(
                SubscriptionInvoice.idempotency_key == key
            )
        )
        if existing:
            continue
        await _create_invoice(
            db,
            tenant_id=sub.tenant_id,
            subscription=sub,
            plan=plan,
            billing_interval=sub.billing_interval,
            purpose=PURPOSE_RENEWAL,
            amount_minor=amount,
            period_start=period_start,
            period_end=period_end,
            idempotency_key=key,
            metadata={"plan": plan.slug},
        )
        created += 1

    if created:
        await db.flush()
    return created


async def mark_past_due_unpaid(db: AsyncSession, *, batch_size: int = 100) -> int:
    now = utc_now()
    result = await db.execute(
        select(SubscriptionInvoice)
        .where(
            SubscriptionInvoice.status == INVOICE_OPEN,
            SubscriptionInvoice.purpose == PURPOSE_RENEWAL,
            SubscriptionInvoice.due_at.is_not(None),
            SubscriptionInvoice.due_at < now,
        )
        .limit(batch_size)
    )
    invoices = list(result.scalars().all())
    updated = 0
    for inv in invoices:
        sub = await db.get(Subscription, inv.subscription_id)
        if sub is None:
            continue
        if sub.status in {STATUS_ACTIVE, STATUS_TRIAL} and not sub.cancel_at_period_end:
            try:
                _assert_transition(sub.status, STATUS_PAST_DUE)
            except HTTPException:
                continue
            old = sub.status
            sub.status = STATUS_PAST_DUE
            _add_event(
                db,
                sub.id,
                "subscription.past_due",
                {
                    "from_status": old,
                    "invoice_public_id": inv.public_id,
                    "source": "maintenance_worker",
                },
            )
            updated += 1
    if updated:
        await db.flush()
    return updated
