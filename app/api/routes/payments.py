from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_company_tenant_owner, get_current_user
from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.tenant import TenantContext
from app.models.entities import PaymentProvider, User
from app.schemas.admin import PaymentCheckoutPreviewRequest, PaymentCheckoutPreviewResponse
from app.schemas.cabinet import PaymentCheckoutCreate, PaymentResponse
from app.schemas.schemas import SubscriptionPlanResponse
from app.services.company_service import get_company_available_plans, list_all_plans
from app.services.payment_service import create_checkout, get_payment, preview_checkout, process_webhook
from app.services.seed_service import seed_subscription_plans

router = APIRouter(tags=["payments"])


def _payment_to_response(payment) -> PaymentResponse:
    return PaymentResponse(
        id=payment.id,
        plan_id=payment.plan_id,
        user_subscription_id=payment.user_subscription_id,
        action=payment.action,
        period_months=payment.period_months,
        provider=payment.provider.value if hasattr(payment.provider, "value") else payment.provider,
        original_amount=payment.original_amount,
        discount_amount=payment.discount_amount,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
        promo_code=payment.promo_code.code if payment.promo_code else None,
        confirmation_url=payment.confirmation_url,
        created_at=payment.created_at,
        paid_at=payment.paid_at,
        plan=SubscriptionPlanResponse.model_validate(payment.plan),
    )


@router.get("/subscription-plans", response_model=list[SubscriptionPlanResponse])
async def list_plans(db: AsyncSession = Depends(get_db)) -> list:
    await seed_subscription_plans(db)
    return await list_all_plans(db)


@router.get("/companies/{company_id}/subscription/available-plans", response_model=list[SubscriptionPlanResponse])
async def list_available_plans_for_company_endpoint(
    tenant: TenantContext = Depends(get_company_tenant_owner),
    db: AsyncSession = Depends(get_db),
) -> list:
    return await get_company_available_plans(db, tenant.company_id)


@router.post("/payments/checkout/preview", response_model=PaymentCheckoutPreviewResponse)
async def checkout_preview(
    data: PaymentCheckoutPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentCheckoutPreviewResponse:
    try:
        return await preview_checkout(
            db,
            current_user,
            data.plan_code,
            data.action,
            data.period_months,
            data.subscription_id,
            data.promo_code,
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/payments/checkout", response_model=PaymentResponse, status_code=201)
async def checkout(
    data: PaymentCheckoutCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    try:
        payment = await create_checkout(
            db,
            current_user,
            data.plan_code,
            data.action,
            data.period_months,
            data.subscription_id,
            data.promo_code,
        )
        return _payment_to_response(payment)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment_status(
    payment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    try:
        payment = await get_payment(db, payment_id, current_user.id)
        return _payment_to_response(payment)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/payments/webhook/{provider}")
async def payment_webhook(
    provider: PaymentProvider,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    payload = await request.json()
    payment = await process_webhook(db, provider, payload)
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    return {"status": payment.status.value, "payment_id": str(payment.id)}
