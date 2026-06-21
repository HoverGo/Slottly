from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_platform_offer_manager
from app.core.database import get_db
from app.core.exceptions import AppError
from app.models.entities import User
from app.schemas.company_offers import (
    CompanySubscriptionOfferResponse,
    CompanySubscriptionOfferUpdate,
    CompanySubscriptionOfferUpsert,
)
from app.services.company_offer_service import (
    get_company_subscription_offer,
    list_company_subscription_offers,
    offer_to_dict,
    update_company_subscription_offer,
    upsert_company_subscription_offer,
)

router = APIRouter(prefix="/admin", tags=["admin-company-offers"])


def _offer_response(offer, *, company_name: str | None = None) -> CompanySubscriptionOfferResponse:
    data = offer_to_dict(offer)
    data["company_name"] = company_name
    return CompanySubscriptionOfferResponse(**data)


@router.get("/company-subscription-offers", response_model=list[CompanySubscriptionOfferResponse])
async def admin_list_company_subscription_offers(
    _: User = Depends(require_platform_offer_manager),
    db: AsyncSession = Depends(get_db),
) -> list[CompanySubscriptionOfferResponse]:
    offers = await list_company_subscription_offers(db)
    result = []
    for offer in offers:
        company_name = offer.company.name if offer.company else None
        result.append(_offer_response(offer, company_name=company_name))
    return result


@router.get(
    "/companies/{company_id}/subscription-offer",
    response_model=CompanySubscriptionOfferResponse,
)
async def admin_get_company_subscription_offer(
    company_id: UUID,
    _: User = Depends(require_platform_offer_manager),
    db: AsyncSession = Depends(get_db),
) -> CompanySubscriptionOfferResponse:
    offer = await get_company_subscription_offer(db, company_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Индивидуальное предложение не найдено")
    company_name = offer.company.name if offer.company else None
    return _offer_response(offer, company_name=company_name)


@router.put(
    "/companies/{company_id}/subscription-offer",
    response_model=CompanySubscriptionOfferResponse,
)
async def admin_upsert_company_subscription_offer(
    company_id: UUID,
    data: CompanySubscriptionOfferUpsert,
    admin: User = Depends(require_platform_offer_manager),
    db: AsyncSession = Depends(get_db),
) -> CompanySubscriptionOfferResponse:
    try:
        offer = await upsert_company_subscription_offer(
            db,
            admin,
            company_id,
            name=data.name,
            display_name=data.display_name,
            price_monthly=data.price_monthly,
            max_users=data.max_users,
            max_branches=data.max_branches,
            max_roles=data.max_roles,
            max_services=data.max_services,
            max_appointments_per_month=data.max_appointments_per_month,
            base_plan_code=data.base_plan_code,
            valid_from=data.valid_from,
            valid_until=data.valid_until,
            is_active=data.is_active,
            description=data.description,
        )
        await db.refresh(offer, ["company"])
        return _offer_response(offer, company_name=offer.company.name if offer.company else None)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.patch(
    "/companies/{company_id}/subscription-offer",
    response_model=CompanySubscriptionOfferResponse,
)
async def admin_update_company_subscription_offer(
    company_id: UUID,
    data: CompanySubscriptionOfferUpdate,
    _: User = Depends(require_platform_offer_manager),
    db: AsyncSession = Depends(get_db),
) -> CompanySubscriptionOfferResponse:
    try:
        offer = await update_company_subscription_offer(
            db,
            company_id,
            name=data.name,
            display_name=data.display_name,
            clear_display_name=data.clear_display_name,
            price_monthly=data.price_monthly,
            max_users=data.max_users,
            max_branches=data.max_branches,
            max_roles=data.max_roles,
            max_services=data.max_services,
            max_appointments_per_month=data.max_appointments_per_month,
            base_plan_code=data.base_plan_code,
            clear_base_plan_code=data.clear_base_plan_code,
            valid_from=data.valid_from,
            valid_until=data.valid_until,
            clear_valid_from=data.clear_valid_from,
            clear_valid_until=data.clear_valid_until,
            is_active=data.is_active,
            description=data.description,
        )
        await db.refresh(offer, ["company"])
        return _offer_response(offer, company_name=offer.company.name if offer.company else None)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
