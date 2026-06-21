from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ForbiddenError
from app.core.permissions import MANAGE_COMPANY, MANAGE_MEMBERS
from app.core.tenant import TenantContext
from app.models.entities import Company, CompanyGalleryPhoto, OrganizationType
from app.repositories.tenant_repository import TenantRepository
from app.schemas.schemas import CompanyWorkingHours
from app.services.booking_slug_service import (
    booking_page_url,
    ensure_unique_booking_slug,
    slug_from_company_name,
    validate_booking_slug_available,
)
from app.services.media_service import media_url
def can_manage_company_profile(tenant: TenantContext) -> bool:
    if tenant.is_owner:
        return True
    return tenant.has_permission(MANAGE_COMPANY) or tenant.has_permission(MANAGE_MEMBERS)


def require_manage_company_profile(tenant: TenantContext) -> None:
    if not can_manage_company_profile(tenant):
        raise ForbiddenError("Нет права на редактирование профиля компании")


def working_hours_to_dict(working_hours: CompanyWorkingHours | None) -> dict | None:
    if working_hours is None:
        return None
    data = working_hours.model_dump(exclude_none=True)
    return data or None


def working_hours_from_dict(data: dict | None) -> CompanyWorkingHours | None:
    if not data:
        return None
    return CompanyWorkingHours.model_validate(data)


def gallery_photo_to_dict(photo: CompanyGalleryPhoto) -> dict:
    return {
        "id": photo.id,
        "url": media_url(photo.path),
        "sort_order": photo.sort_order,
        "created_at": photo.created_at,
    }


def company_to_response(
    company: Company,
    *,
    has_sub: bool,
    is_owner: bool,
    gallery: list[CompanyGalleryPhoto] | None = None,
    rating_average: float = 0.0,
    rating_count: int = 0,
) -> dict:
    logo = media_url(company.photo_path)
    org_type = company.organization_type.value if company.organization_type else None
    return {
        "id": company.id,
        "name": company.name,
        "owner_id": company.owner_id,
        "country": company.country,
        "city": company.city,
        "address": company.address,
        "phone": company.phone,
        "organization_type": org_type,
        "working_hours": working_hours_from_dict(company.working_hours),
        "logo_url": logo,
        "photo_url": logo,
        "gallery": [gallery_photo_to_dict(p) for p in (gallery or [])],
        "booking_slug": company.booking_slug,
        "public_booking_enabled": company.public_booking_enabled,
        "booking_url": booking_page_url(company.booking_slug)
        if company.public_booking_enabled and company.booking_slug
        else None,
        "rating_average": rating_average,
        "rating_count": rating_count,
        "is_owner_first_company": company.is_owner_first_company,
        "created_at": company.created_at,
        "updated_at": company.updated_at,
        "has_active_subscription": has_sub,
        "is_owner": is_owner,
    }


def _clean_optional_text(value: str | None, *, max_len: int) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > max_len:
        raise AppError(f"Длина поля не более {max_len} символов")
    return cleaned


async def update_company_profile(
    db: AsyncSession,
    tenant: TenantContext,
    *,
    name: str | None = None,
    country: str | None = None,
    city: str | None = None,
    address: str | None = None,
    phone: str | None = None,
    organization_type: str | None = None,
    working_hours: CompanyWorkingHours | None = None,
    clear_country: bool = False,
    clear_city: bool = False,
    clear_address: bool = False,
    clear_phone: bool = False,
    clear_organization_type: bool = False,
    clear_working_hours: bool = False,
    booking_slug: str | None = None,
    public_booking_enabled: bool | None = None,
) -> Company:
    require_manage_company_profile(tenant)
    company = tenant.company

    if name is not None:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise AppError("Название компании обязательно")
        company.name = cleaned_name

    if clear_country:
        company.country = None
    elif country is not None:
        company.country = _clean_optional_text(country, max_len=100)

    if clear_city:
        company.city = None
    elif city is not None:
        company.city = _clean_optional_text(city, max_len=100)

    if clear_address:
        company.address = None
    elif address is not None:
        company.address = _clean_optional_text(address, max_len=500)

    if clear_phone:
        company.phone = None
    elif phone is not None:
        company.phone = _clean_optional_text(phone, max_len=50)

    if clear_organization_type:
        company.organization_type = None
    elif organization_type is not None:
        company.organization_type = OrganizationType(organization_type)

    if clear_working_hours:
        company.working_hours = None
    elif working_hours is not None:
        company.working_hours = working_hours_to_dict(working_hours)

    if public_booking_enabled is not None:
        company.public_booking_enabled = public_booking_enabled

    if booking_slug is not None:
        if booking_slug.strip():
            company.booking_slug = await validate_booking_slug_available(
                db, booking_slug, exclude_company_id=company.id
            )
        else:
            company.booking_slug = None

    if company.public_booking_enabled and not company.booking_slug:
        generated = slug_from_company_name(company.name)
        company.booking_slug = await ensure_unique_booking_slug(
            db, generated, exclude_company_id=company.id
        )

    company.updated_at = datetime.now(UTC)
    await db.flush()
    return company


async def list_company_gallery(db: AsyncSession, company_id: UUID) -> list[CompanyGalleryPhoto]:
    repo = TenantRepository(db, company_id)
    return await repo.list_gallery_photos()
