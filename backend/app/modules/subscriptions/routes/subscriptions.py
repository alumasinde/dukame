from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models.identity import User
from app.modules.auth.security import get_current_user
from app.modules.rbac.services.rbac import require_permission
from app.modules.subscriptions.entitlements import feature_limit
from app.modules.subscriptions.models.billing import SubscriptionInvoice
from app.modules.subscriptions.models.subscription import Plan, Subscription
from app.modules.subscriptions.schemas.subscription import (
    PlanResponse,
    SubscriptionCancelRequest,
    SubscriptionChangeRequest,
    SubscriptionEventResponse,
    SubscriptionInvoiceResponse,
    SubscriptionMarkPaidRequest,
    SubscriptionPayInvoiceRequest,
    SubscriptionPaymentResponse,
    SubscriptionResponse,
    SubscriptionUpgradeRequest,
    UpgradeResponse,
    UsageItemResponse,
    UsageSnapshotResponse,
)
from app.modules.subscriptions.services.billing import (
    INVOICE_OPEN,
    INVOICE_PAID,
    create_upgrade_invoice,
    get_invoice_by_public_id,
    initiate_invoice_payment,
    list_tenant_invoices,
    mark_invoice_paid_manual,
)
from app.modules.subscriptions.services.subscription import (
    cancel_subscription,
    change_subscription,
    get_tenant_subscription,
    is_entitled,
    list_active_plans,
    list_subscription_events,
    reactivate_subscription,
)
from app.modules.subscriptions.services.usage import period_key_for, usage_snapshot
from app.modules.tenancy.models.tenant import Tenant
from app.modules.tenancy.services.tenant import get_tenant_by_public_id

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def plan_response(plan: Plan) -> PlanResponse:
    return PlanResponse.model_validate(plan, from_attributes=True)


def subscription_response(subscription: Subscription) -> SubscriptionResponse:
    return SubscriptionResponse(
        public_id=subscription.public_id,
        status=subscription.status,
        billing_interval=subscription.billing_interval,
        starts_at=subscription.starts_at,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        entitled=is_entitled(subscription),
        plan=plan_response(subscription.plan),
    )


def payment_response(payment) -> SubscriptionPaymentResponse:
    return SubscriptionPaymentResponse.model_validate(payment, from_attributes=True)


async def invoice_response(
    db: AsyncSession, invoice: SubscriptionInvoice
) -> SubscriptionInvoiceResponse:
    plan = await db.scalar(select(Plan).where(Plan.id == invoice.plan_id))
    payments = [
        payment_response(p)
        for p in sorted(invoice.payments or [], key=lambda x: x.created_at)
    ]
    return SubscriptionInvoiceResponse(
        public_id=invoice.public_id,
        status=invoice.status,
        purpose=invoice.purpose,
        billing_interval=invoice.billing_interval,
        currency=invoice.currency,
        amount_minor=invoice.amount_minor,
        period_start=invoice.period_start,
        period_end=invoice.period_end,
        due_at=invoice.due_at,
        paid_at=invoice.paid_at,
        plan_public_id=plan.public_id if plan else None,
        payments=payments,
        created_at=invoice.created_at,
    )


async def authorized_tenant(
    db: AsyncSession, user: User, tenant_public_id: str, permission: str
) -> Tenant:
    tenant = await get_tenant_by_public_id(db, tenant_public_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    await require_permission(db, user, tenant.id, permission)
    return tenant


@router.get("/plans", response_model=list[PlanResponse])
async def plans(db: AsyncSession = Depends(get_db)) -> list[PlanResponse]:
    return [plan_response(plan) for plan in await list_active_plans(db)]


@router.get("/{tenant_public_id}", response_model=SubscriptionResponse)
async def current_subscription(
    tenant_public_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    tenant = await authorized_tenant(db, user, tenant_public_id, "subscription.read")
    subscription = await get_tenant_subscription(db, user, tenant.public_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription_response(subscription)


@router.get("/{tenant_public_id}/features", response_model=dict[str, Any])
async def features(
    tenant_public_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    tenant = await authorized_tenant(db, user, tenant_public_id, "subscription.read")
    subscription = await get_tenant_subscription(db, user, tenant.public_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    if not is_entitled(subscription):
        return {}
    return {feature.feature_key: feature.value for feature in subscription.plan.features}


@router.get(
    "/{tenant_public_id}/events",
    response_model=list[SubscriptionEventResponse],
)
async def events(
    tenant_public_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SubscriptionEventResponse]:
    tenant = await authorized_tenant(db, user, tenant_public_id, "subscription.read")
    subscription = await get_tenant_subscription(db, user, tenant.public_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    rows = await list_subscription_events(db, subscription.id, limit=limit)
    return [
        SubscriptionEventResponse.model_validate(row, from_attributes=True) for row in rows
    ]


@router.get(
    "/{tenant_public_id}/invoices",
    response_model=list[SubscriptionInvoiceResponse],
)
async def invoices(
    tenant_public_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SubscriptionInvoiceResponse]:
    tenant = await authorized_tenant(db, user, tenant_public_id, "subscription.read")
    rows = await list_tenant_invoices(db, tenant.id, limit=limit)
    return [await invoice_response(db, row) for row in rows]


@router.get(
    "/{tenant_public_id}/usage",
    response_model=UsageSnapshotResponse,
)
async def usage(
    tenant_public_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsageSnapshotResponse:
    tenant = await authorized_tenant(db, user, tenant_public_id, "subscription.read")
    subscription = await get_tenant_subscription(db, user, tenant.public_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    keys = [f.feature_key for f in subscription.plan.features]
    period = period_key_for()
    snapshot = await usage_snapshot(db, tenant.id, keys, period_key=period)
    items = [
        UsageItemResponse(
            feature_key=key,
            quantity=snapshot.get(key, 0),
            limit=feature_limit(subscription, key),
            period_key=period,
        )
        for key in keys
    ]
    return UsageSnapshotResponse(period_key=period, items=items)


@router.post("/{tenant_public_id}/change", response_model=SubscriptionResponse)
async def change(
    tenant_public_id: str,
    payload: SubscriptionChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    tenant = await authorized_tenant(db, user, tenant_public_id, "subscription.manage")
    subscription = await change_subscription(
        db, user, tenant.public_id, payload.plan_public_id, payload.billing_interval
    )
    await db.commit()
    return subscription_response(subscription)


@router.post("/{tenant_public_id}/upgrade", response_model=UpgradeResponse)
async def upgrade(
    tenant_public_id: str,
    payload: SubscriptionUpgradeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UpgradeResponse:
    tenant = await authorized_tenant(db, user, tenant_public_id, "subscription.manage")
    subscription, invoice = await create_upgrade_invoice(
        db,
        user,
        tenant.public_id,
        payload.plan_public_id,
        payload.billing_interval,
    )
    payment = None
    # Reload subscription after possible zero-amount auto-apply
    subscription = await get_tenant_subscription(db, user, tenant.public_id)
    assert subscription is not None
    invoice = await get_invoice_by_public_id(db, invoice.public_id)
    assert invoice is not None

    if invoice.status == INVOICE_OPEN:
        if not payload.phone:
            raise HTTPException(
                status_code=422,
                detail="phone is required to initiate payment for an open invoice",
            )
        payment = await initiate_invoice_payment(db, invoice, phone=payload.phone)
        invoice = await get_invoice_by_public_id(db, invoice.public_id)
        assert invoice is not None

    await db.commit()
    return UpgradeResponse(
        subscription=subscription_response(subscription),
        invoice=await invoice_response(db, invoice),
        payment=payment_response(payment) if payment else None,
    )


@router.post(
    "/{tenant_public_id}/invoices/{invoice_public_id}/pay",
    response_model=SubscriptionPaymentResponse,
)
async def pay_invoice(
    tenant_public_id: str,
    invoice_public_id: str,
    payload: SubscriptionPayInvoiceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionPaymentResponse:
    tenant = await authorized_tenant(db, user, tenant_public_id, "subscription.manage")
    invoice = await get_invoice_by_public_id(db, invoice_public_id)
    if invoice is None or invoice.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Invoice not found")
    payment = await initiate_invoice_payment(db, invoice, phone=payload.phone)
    await db.commit()
    return payment_response(payment)


@router.post(
    "/{tenant_public_id}/invoices/{invoice_public_id}/mark-paid",
    response_model=UpgradeResponse,
)
async def mark_invoice_paid(
    tenant_public_id: str,
    invoice_public_id: str,
    payload: SubscriptionMarkPaidRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UpgradeResponse:
    """Mark an open invoice as paid (support / offline payment / M-Pesa disabled)."""
    tenant = await authorized_tenant(db, user, tenant_public_id, "subscription.manage")
    invoice = await get_invoice_by_public_id(db, invoice_public_id)
    if invoice is None or invoice.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status != INVOICE_OPEN:
        raise HTTPException(
            status_code=409,
            detail={"code": "invoice_not_open", "status": invoice.status},
        )
    subscription = await mark_invoice_paid_manual(
        db, invoice=invoice, actor_user_id=user.id, note=payload.note
    )
    invoice = await get_invoice_by_public_id(db, invoice_public_id)
    assert invoice is not None and invoice.status == INVOICE_PAID
    await db.commit()
    return UpgradeResponse(
        subscription=subscription_response(subscription),
        invoice=await invoice_response(db, invoice),
        payment=None,
    )


@router.post("/{tenant_public_id}/cancel", response_model=SubscriptionResponse)
async def cancel(
    tenant_public_id: str,
    payload: SubscriptionCancelRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    tenant = await authorized_tenant(db, user, tenant_public_id, "subscription.manage")
    subscription = await cancel_subscription(
        db, user, tenant.public_id, payload.immediately
    )
    await db.commit()
    return subscription_response(subscription)


@router.post("/{tenant_public_id}/reactivate", response_model=SubscriptionResponse)
async def reactivate(
    tenant_public_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    tenant = await authorized_tenant(db, user, tenant_public_id, "subscription.manage")
    subscription = await reactivate_subscription(db, user, tenant.public_id)
    await db.commit()
    return subscription_response(subscription)
