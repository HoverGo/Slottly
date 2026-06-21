from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_company_tenant, get_current_user, require_permission
from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.permissions import (
    MANAGE_BRANCHES,
    MANAGE_JOIN_REQUESTS,
    MANAGE_MEMBERS,
    MANAGE_ROLES,
)
from app.core.tenant import TenantContext
from app.models.entities import Branch, CompanyMember, CompanyRole, CompensationType, User
from app.repositories.tenant_repository import TenantRepository
from app.schemas.cabinet import JoinRequestCreate, JoinRequestResponse
from app.schemas.schemas import (
    BranchCreate,
    BranchResponse,
    CompanyCreate,
    CompanyGalleryPhotoResponse,
    CompanyMemberResponse,
    CompanyMemberUpdate,
    CompanyResponse,
    CompanyRequisitesResponse,
    CompanyRequisitesUpdate,
    CompanyRoleCreate,
    CompanyRoleResponse,
    CompanyRoleUpdate,
    CompanyUpdate,
    SubscriptionLimitsResponse,
)
from app.services.company_profile_service import (
    company_to_response,
    list_company_gallery,
    update_company_profile,
)
from app.services.company_requisites_service import (
    get_company_requisites_or_404,
    requisites_to_dict,
    upsert_company_requisites,
)
from app.services.company_service import (
    create_branch,
    create_company,
    create_role,
    get_active_subscription,
    get_subscription_limits,
    list_accessible_companies,
)
from app.services.join_request_service import create_join_request, join_request_response_data, list_company_join_requests
from app.services.media_service import (
    delete_company_gallery_photo,
    delete_company_photo,
    delete_member_photo,
    media_url,
    upload_company_gallery_photo,
    upload_company_photo,
    upload_member_photo,
)
from app.services.member_service import update_member, update_role

router = APIRouter(prefix="/companies", tags=["companies"])


async def _build_company_response(
    db: AsyncSession,
    company,
    *,
    has_sub: bool,
    is_owner: bool,
    include_gallery: bool = False,
    include_rating: bool = False,
) -> CompanyResponse:
    from app.services.review_service import get_rating_summary

    gallery = await list_company_gallery(db, company.id) if include_gallery else []
    rating_average = 0.0
    rating_count = 0
    if include_rating:
        rating = await get_rating_summary(db, company.id)
        rating_average = rating["average"]
        rating_count = rating["count"]
    return CompanyResponse(
        **company_to_response(
            company,
            has_sub=has_sub,
            is_owner=is_owner,
            gallery=gallery,
            rating_average=rating_average,
            rating_count=rating_count,
        )
    )


def _member_response(member: CompanyMember) -> CompanyMemberResponse:
    comp_type = member.compensation_type.value if member.compensation_type else None
    return CompanyMemberResponse(
        id=member.id,
        company_id=member.company_id,
        user_id=member.user_id,
        role_id=member.role_id,
        compensation_type=comp_type,
        compensation_rate=member.compensation_rate,
        compensation_percent=member.compensation_percent,
        photo_url=media_url(member.photo_path),
        created_at=member.created_at,
    )


@router.post("", response_model=CompanyResponse, status_code=201)
async def create_new_company(
    data: CompanyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompanyResponse:
    try:
        company = await create_company(db, current_user, data.name, data.subscription_id)
        return await _build_company_response(db, company, has_sub=True, is_owner=True)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("", response_model=list[CompanyResponse])
async def list_my_companies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CompanyResponse]:
    accessible = await list_accessible_companies(db, current_user.id)
    responses = []
    for company, is_owner in accessible:
        sub = await get_active_subscription(db, company.id)
        responses.append(
            await _build_company_response(
                db, company, has_sub=sub is not None, is_owner=is_owner, include_gallery=False
            )
        )
    return responses


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> CompanyResponse:
    sub = await get_active_subscription(db, tenant.company_id)
    return await _build_company_response(
        db,
        tenant.company,
        has_sub=sub is not None,
        is_owner=tenant.is_owner,
        include_gallery=True,
        include_rating=True,
    )


@router.patch("/{company_id}", response_model=CompanyResponse)
async def patch_company(
    data: CompanyUpdate,
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> CompanyResponse:
    try:
        company = await update_company_profile(
            db,
            tenant,
            name=data.name,
            country=data.country,
            city=data.city,
            address=data.address,
            phone=data.phone,
            organization_type=data.organization_type,
            working_hours=data.working_hours,
            clear_country=data.clear_country,
            clear_city=data.clear_city,
            clear_address=data.clear_address,
            clear_phone=data.clear_phone,
            clear_organization_type=data.clear_organization_type,
            clear_working_hours=data.clear_working_hours,
            booking_slug=data.booking_slug,
            public_booking_enabled=data.public_booking_enabled,
        )
        sub = await get_active_subscription(db, tenant.company_id)
        return await _build_company_response(
            db, company, has_sub=sub is not None, is_owner=tenant.is_owner, include_gallery=True, include_rating=True
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/{company_id}/requisites", response_model=CompanyRequisitesResponse)
async def get_company_requisites_endpoint(
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> CompanyRequisitesResponse:
    try:
        requisites = await get_company_requisites_or_404(db, tenant.company_id)
        return CompanyRequisitesResponse(**requisites_to_dict(requisites))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.put("/{company_id}/requisites", response_model=CompanyRequisitesResponse)
async def upsert_company_requisites_endpoint(
    data: CompanyRequisitesUpdate,
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> CompanyRequisitesResponse:
    try:
        requisites = await upsert_company_requisites(
            db,
            tenant,
            name=data.name,
            inn=data.inn,
            kpp=data.kpp,
            billing_email=str(data.billing_email),
        )
        return CompanyRequisitesResponse(**requisites_to_dict(requisites))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/{company_id}/limits", response_model=SubscriptionLimitsResponse)
async def get_limits(
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionLimitsResponse:
    limits = await get_subscription_limits(db, tenant.company)
    return SubscriptionLimitsResponse(**limits)


@router.post("/{company_id}/roles", response_model=CompanyRoleResponse, status_code=201)
async def create_company_role(
    data: CompanyRoleCreate,
    tenant: TenantContext = Depends(require_permission(MANAGE_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> CompanyRole:
    try:
        return await create_role(db, tenant, data.name, data.description, data.permissions)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.patch("/{company_id}/roles/{role_id}", response_model=CompanyRoleResponse)
async def patch_company_role(
    role_id: UUID,
    data: CompanyRoleUpdate,
    tenant: TenantContext = Depends(require_permission(MANAGE_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> CompanyRole:
    try:
        return await update_role(
            db,
            tenant,
            role_id,
            name=data.name,
            description=data.description,
            permissions=data.permissions,
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/{company_id}/roles", response_model=list[CompanyRoleResponse])
async def list_company_roles(
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[CompanyRole]:
    repo = TenantRepository(db, tenant.company_id)
    return await repo.list_roles()


@router.post("/{company_id}/join-requests", response_model=JoinRequestResponse, status_code=201)
async def invite_user(
    data: JoinRequestCreate,
    tenant: TenantContext = Depends(require_permission(MANAGE_JOIN_REQUESTS)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JoinRequestResponse:
    try:
        comp_type = CompensationType(data.compensation_type) if data.compensation_type else None
        request = await create_join_request(
            db,
            tenant,
            current_user,
            data.email,
            data.role_id,
            data.message,
            full_name=data.full_name,
            phone=data.phone,
            compensation_type=comp_type,
            compensation_rate=data.compensation_rate,
            compensation_percent=data.compensation_percent,
        )
        return JoinRequestResponse(**join_request_response_data(request))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/{company_id}/join-requests", response_model=list[JoinRequestResponse])
async def list_join_requests(
    tenant: TenantContext = Depends(require_permission(MANAGE_JOIN_REQUESTS)),
    db: AsyncSession = Depends(get_db),
) -> list[JoinRequestResponse]:
    requests = await list_company_join_requests(db, tenant.company_id)
    return [JoinRequestResponse(**join_request_response_data(r)) for r in requests]


@router.get("/{company_id}/members", response_model=list[CompanyMemberResponse])
async def list_company_members(
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[CompanyMemberResponse]:
    repo = TenantRepository(db, tenant.company_id)
    members = await repo.list_members()
    return [_member_response(member) for member in members]


@router.post("/{company_id}/photo", response_model=CompanyResponse)
async def upload_company_photo_endpoint(
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
) -> CompanyResponse:
    try:
        company = await upload_company_photo(db, tenant, file)
        sub = await get_active_subscription(db, tenant.company_id)
        return await _build_company_response(
            db, company, has_sub=sub is not None, is_owner=tenant.is_owner, include_gallery=True
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.delete("/{company_id}/photo", response_model=CompanyResponse)
async def delete_company_photo_endpoint(
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> CompanyResponse:
    try:
        company = await delete_company_photo(db, tenant)
        sub = await get_active_subscription(db, tenant.company_id)
        return await _build_company_response(
            db, company, has_sub=sub is not None, is_owner=tenant.is_owner, include_gallery=True
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/{company_id}/logo",
    response_model=CompanyResponse,
    include_in_schema=True,
)
async def upload_company_logo_endpoint(
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
) -> CompanyResponse:
    return await upload_company_photo_endpoint(tenant=tenant, db=db, file=file)


@router.delete("/{company_id}/logo", response_model=CompanyResponse)
async def delete_company_logo_endpoint(
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> CompanyResponse:
    return await delete_company_photo_endpoint(tenant=tenant, db=db)


@router.post(
    "/{company_id}/gallery",
    response_model=CompanyGalleryPhotoResponse,
    status_code=201,
)
async def upload_company_gallery_photo_endpoint(
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
) -> CompanyGalleryPhotoResponse:
    try:
        from app.services.company_profile_service import gallery_photo_to_dict

        photo = await upload_company_gallery_photo(db, tenant, file)
        return CompanyGalleryPhotoResponse(**gallery_photo_to_dict(photo))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.delete("/{company_id}/gallery/{photo_id}", status_code=204)
async def delete_company_gallery_photo_endpoint(
    photo_id: UUID,
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await delete_company_gallery_photo(db, tenant, photo_id)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/{company_id}/members/{member_id}/photo", response_model=CompanyMemberResponse)
async def upload_member_photo_endpoint(
    member_id: UUID,
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
) -> CompanyMemberResponse:
    try:
        member = await upload_member_photo(db, tenant, member_id, file)
        return _member_response(member)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.delete("/{company_id}/members/{member_id}/photo", response_model=CompanyMemberResponse)
async def delete_member_photo_endpoint(
    member_id: UUID,
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> CompanyMemberResponse:
    try:
        member = await delete_member_photo(db, tenant, member_id)
        return _member_response(member)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.patch("/{company_id}/members/{member_id}", response_model=CompanyMemberResponse)
async def patch_member(
    member_id: UUID,
    data: CompanyMemberUpdate,
    tenant: TenantContext = Depends(require_permission(MANAGE_MEMBERS)),
    db: AsyncSession = Depends(get_db),
) -> CompanyMemberResponse:
    try:
        comp_type = CompensationType(data.compensation_type) if data.compensation_type else None
        member = await update_member(
            db,
            tenant,
            member_id,
            role_id=data.role_id,
            compensation_type=comp_type,
            compensation_rate=data.compensation_rate,
            compensation_percent=data.compensation_percent,
            clear_compensation=data.clear_compensation,
        )
        return _member_response(member)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/{company_id}/branches", response_model=BranchResponse, status_code=201)
async def create_company_branch(
    data: BranchCreate,
    tenant: TenantContext = Depends(require_permission(MANAGE_BRANCHES)),
    db: AsyncSession = Depends(get_db),
) -> Branch:
    try:
        return await create_branch(db, tenant, data.name, data.address)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/{company_id}/branches", response_model=list[BranchResponse])
async def list_company_branches(
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[Branch]:
    repo = TenantRepository(db, tenant.company_id)
    return await repo.list_branches()
