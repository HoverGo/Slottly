from uuid import UUID



from sqlalchemy.ext.asyncio import AsyncSession



from app.core.exceptions import AppError, NotFoundError

from app.core.tenant import TenantContext

from app.models.entities import CompanyService

from app.repositories.tenant_repository import TenantRepository



MIN_DURATION = 5

MAX_DURATION = 480

ALLOWED_BUFFER_MINUTES = {0, 5, 10, 15, 30}





def _validate_duration(duration_minutes: int) -> None:

    if duration_minutes < MIN_DURATION or duration_minutes > MAX_DURATION:

        raise AppError(f"Длительность услуги: от {MIN_DURATION} до {MAX_DURATION} минут")





def _validate_buffer(value: int, field_label: str) -> None:

    if value not in ALLOWED_BUFFER_MINUTES:

        raise AppError(f"{field_label}: допустимые значения 0, 5, 10, 15, 30 минут")





async def _validate_member_and_branch(

    repo: TenantRepository,

    *,

    member_id: UUID | None,

    branch_id: UUID | None,

) -> None:

    if member_id is not None:

        member = await repo.get_member_by_id(member_id)

        if not member:

            raise NotFoundError("Сотрудник не найден в компании")

    if branch_id is not None:

        branch = await repo.get_branch_by_id(branch_id)

        if not branch:

            raise NotFoundError("Филиал не найден в компании")





def service_to_response(service: CompanyService) -> dict:

    member_user = service.member.user if service.member else None

    return {

        "id": service.id,

        "company_id": service.company_id,

        "name": service.name,

        "category": service.category,

        "description": service.description,

        "duration_minutes": service.duration_minutes,

        "buffer_before_minutes": service.buffer_before_minutes,

        "buffer_after_minutes": service.buffer_after_minutes,

        "price": service.price,

        "member_id": service.member_id,

        "member_name": member_user.full_name if member_user else None,

        "branch_id": service.branch_id,

        "is_active": service.is_active,

        "created_by_id": service.created_by_id,

        "created_at": service.created_at,

    }





async def create_company_service(

    db: AsyncSession,

    tenant: TenantContext,

    *,

    name: str,

    duration_minutes: int,

    category: str | None = None,

    description: str | None = None,

    buffer_before_minutes: int = 0,

    buffer_after_minutes: int = 0,

    price: int | None = None,

    member_id: UUID | None = None,

    branch_id: UUID | None = None,

) -> CompanyService:

    from app.services.company_service import check_subscription_limit, require_active_subscription



    await require_active_subscription(db, tenant.company)

    await check_subscription_limit(db, tenant.company, add_services=1)

    _validate_duration(duration_minutes)

    _validate_buffer(buffer_before_minutes, "Буфер до услуги")

    _validate_buffer(buffer_after_minutes, "Буфер после услуги")



    repo = TenantRepository(db, tenant.company_id)

    await _validate_member_and_branch(repo, member_id=member_id, branch_id=branch_id)



    service = CompanyService(

        company_id=tenant.company_id,

        name=name,

        category=category.strip() if category and category.strip() else None,

        description=description,

        duration_minutes=duration_minutes,

        buffer_before_minutes=buffer_before_minutes,

        buffer_after_minutes=buffer_after_minutes,

        price=price,

        member_id=member_id,

        branch_id=branch_id,

        created_by_id=tenant.user_id,

    )

    db.add(service)

    await db.flush()

    await db.refresh(service, ["member"])

    if service.member:

        await db.refresh(service.member, ["user"])

    return service





async def list_company_services(

    db: AsyncSession,

    company_id: UUID,

    *,

    active_only: bool = False,

    member_id: UUID | None = None,

) -> list[CompanyService]:

    repo = TenantRepository(db, company_id)

    return await repo.list_services(active_only=active_only, member_id=member_id)





async def get_company_service(db: AsyncSession, company_id: UUID, service_id: UUID) -> CompanyService:

    repo = TenantRepository(db, company_id)

    service = await repo.get_service_by_id(service_id)

    if not service:

        raise NotFoundError("Услуга не найдена")

    return service





async def update_company_service(

    db: AsyncSession,

    tenant: TenantContext,

    service_id: UUID,

    *,

    name: str | None = None,

    category: str | None = None,

    description: str | None = None,

    duration_minutes: int | None = None,

    buffer_before_minutes: int | None = None,

    buffer_after_minutes: int | None = None,

    price: int | None = None,

    member_id: UUID | None = None,

    branch_id: UUID | None = None,

    is_active: bool | None = None,

    clear_member: bool = False,

    clear_branch: bool = False,

    clear_category: bool = False,

) -> CompanyService:

    from app.services.company_service import require_active_subscription



    await require_active_subscription(db, tenant.company)



    service = await get_company_service(db, tenant.company_id, service_id)

    repo = TenantRepository(db, tenant.company_id)



    if duration_minutes is not None:

        _validate_duration(duration_minutes)

        service.duration_minutes = duration_minutes

    if buffer_before_minutes is not None:

        _validate_buffer(buffer_before_minutes, "Буфер до услуги")

        service.buffer_before_minutes = buffer_before_minutes

    if buffer_after_minutes is not None:

        _validate_buffer(buffer_after_minutes, "Буфер после услуги")

        service.buffer_after_minutes = buffer_after_minutes

    if name is not None:

        service.name = name

    if clear_category:

        service.category = None

    elif category is not None:

        service.category = category.strip() if category.strip() else None

    if description is not None:

        service.description = description

    if price is not None:

        service.price = price

    if is_active is not None:

        service.is_active = is_active



    if clear_member:

        service.member_id = None

    elif member_id is not None:

        await _validate_member_and_branch(repo, member_id=member_id, branch_id=None)

        service.member_id = member_id



    if clear_branch:

        service.branch_id = None

    elif branch_id is not None:

        await _validate_member_and_branch(repo, member_id=None, branch_id=branch_id)

        service.branch_id = branch_id



    await db.flush()

    await db.refresh(service, ["member"])

    if service.member:

        await db.refresh(service.member, ["user"])

    return service

