from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.core.tenant import TenantContext
from app.models.entities import CompanyRequisites
from app.repositories.tenant_repository import TenantRepository
from app.services.company_profile_service import require_manage_company_profile


def requisites_to_dict(requisites: CompanyRequisites) -> dict:
    return {
        "id": requisites.id,
        "company_id": requisites.company_id,
        "name": requisites.legal_name,
        "inn": requisites.inn,
        "kpp": requisites.kpp,
        "billing_email": requisites.billing_email,
        "created_at": requisites.created_at,
        "updated_at": requisites.updated_at,
    }


async def get_company_requisites(
    db: AsyncSession,
    company_id: UUID,
) -> CompanyRequisites | None:
    repo = TenantRepository(db, company_id)
    return await repo.get_requisites()


async def get_company_requisites_or_404(
    db: AsyncSession,
    company_id: UUID,
) -> CompanyRequisites:
    requisites = await get_company_requisites(db, company_id)
    if not requisites:
        raise NotFoundError("Реквизиты организации не заполнены")
    return requisites


async def upsert_company_requisites(
    db: AsyncSession,
    tenant: TenantContext,
    *,
    name: str,
    inn: str,
    kpp: str | None,
    billing_email: str,
) -> CompanyRequisites:
    require_manage_company_profile(tenant)
    repo = TenantRepository(db, tenant.company_id)
    requisites = await repo.get_requisites()

    cleaned_name = name.strip()
    if not cleaned_name:
        raise AppError("Название организации обязательно")

    if requisites:
        requisites.legal_name = cleaned_name
        requisites.inn = inn
        requisites.kpp = kpp
        requisites.billing_email = billing_email.strip().lower()
        requisites.updated_at = datetime.now(UTC)
    else:
        requisites = CompanyRequisites(
            company_id=tenant.company_id,
            legal_name=cleaned_name,
            inn=inn,
            kpp=kpp,
            billing_email=billing_email.strip().lower(),
        )
        db.add(requisites)

    await db.flush()
    return requisites
