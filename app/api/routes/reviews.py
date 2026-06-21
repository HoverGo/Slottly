from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_company_tenant
from app.core.database import get_db
from app.core.tenant import TenantContext
from app.schemas.reviews import CompanyReviewResponse, CompanyReviewsPageResponse, CompanyRatingSummary
from app.services.review_service import list_company_reviews, review_to_dict

router = APIRouter(prefix="/companies/{company_id}/reviews", tags=["reviews"])


@router.get("", response_model=CompanyReviewsPageResponse)
async def list_reviews(
    limit: int = Query(default=100, ge=1, le=500),
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> CompanyReviewsPageResponse:
    rating, reviews = await list_company_reviews(db, tenant.company_id, limit=limit)
    return CompanyReviewsPageResponse(
        rating=CompanyRatingSummary(**rating),
        reviews=[CompanyReviewResponse(**review_to_dict(review)) for review in reviews],
    )
