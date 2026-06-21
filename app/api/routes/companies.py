from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
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
from app.models.entities import Branch, CompanyMember, CompanyRole, User
from app.repositories.tenant_repository import TenantRepository
from app.schemas.cabinet import JoinRequestCreate, JoinRequestResponse
from app.schemas.schemas import (
    BranchCreate,
    BranchResponse,
    CompanyCreate,
    CompanyMemberResponse,
    CompanyMemberUpdate,
    CompanyResponse,
    CompanyRoleCreate,
    CompanyRoleResponse,
    CompanyRoleUpdate,
    SubscriptionLimitsResponse,
)
from app.services.company_service import (
    create_branch,
    create_company,
    create_role,
    get_active_subscription,
    get_subscription_limits,
    list_accessible_companies,
)
from app.services.join_request_service import create_join_request, list_company_join_requests
from app.services.member_service import change_member_role, update_role

router = APIRouter(prefix="/companies", tags=["companies"])


def _company_response(company, has_sub: bool, is_owner: bool) -> CompanyResponse:
    return CompanyResponse(
        id=company.id,
        name=company.name,
        owner_id=company.owner_id,
        is_owner_first_company=company.is_owner_first_company,
        created_at=company.created_at,
        has_active_subscription=has_sub,
        is_owner=is_owner,
    )


@router.post("", response_model=CompanyResponse, status_code=201)
async def create_new_company(
    data: CompanyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompanyResponse:
    try:
        company = await create_company(db, current_user, data.name, data.subscription_id)
        return _company_response(company, has_sub=True, is_owner=True)
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
        responses.append(_company_response(company, has_sub=sub is not None, is_owner=is_owner))
    return responses


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> CompanyResponse:
    sub = await get_active_subscription(db, tenant.company_id)
    return _company_response(tenant.company, has_sub=sub is not None, is_owner=tenant.is_owner)


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
        request = await create_join_request(
            db, tenant, current_user, data.email, data.role_id, data.message
        )
        return JoinRequestResponse(
            id=request.id,
            company_id=request.company_id,
            user_id=request.user_id,
            role_id=request.role_id,
            invited_by_id=request.invited_by_id,
            status=request.status,
            message=request.message,
            created_at=request.created_at,
            responded_at=request.responded_at,
            role_name=request.role.name if request.role else None,
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/{company_id}/join-requests", response_model=list[JoinRequestResponse])
async def list_join_requests(
    tenant: TenantContext = Depends(require_permission(MANAGE_JOIN_REQUESTS)),
    db: AsyncSession = Depends(get_db),
) -> list[JoinRequestResponse]:
    requests = await list_company_join_requests(db, tenant.company_id)
    return [
        JoinRequestResponse(
            id=r.id,
            company_id=r.company_id,
            user_id=r.user_id,
            role_id=r.role_id,
            invited_by_id=r.invited_by_id,
            status=r.status,
            message=r.message,
            created_at=r.created_at,
            responded_at=r.responded_at,
            role_name=r.role.name if r.role else None,
            invited_by_name=r.invited_by.full_name if r.invited_by else None,
        )
        for r in requests
    ]


@router.get("/{company_id}/members", response_model=list[CompanyMemberResponse])
async def list_company_members(
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
):
    repo = TenantRepository(db, tenant.company_id)
    return await repo.list_members()


@router.patch("/{company_id}/members/{member_id}", response_model=CompanyMemberResponse)
async def patch_member_role(
    member_id: UUID,
    data: CompanyMemberUpdate,
    tenant: TenantContext = Depends(require_permission(MANAGE_MEMBERS)),
    db: AsyncSession = Depends(get_db),
) -> CompanyMember:
    try:
        return await change_member_role(db, tenant, member_id, data.role_id)
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
