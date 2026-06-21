from contextvars import ContextVar
from dataclasses import dataclass, field
from uuid import UUID

from app.models.entities import Company, CompanyMember

_current_tenant: ContextVar["TenantContext | None"] = ContextVar("current_tenant", default=None)


@dataclass(frozen=True, slots=True)
class TenantContext:
    """Контекст текущей компании — все операции только в её рамках"""

    company_id: UUID
    company: Company
    user_id: UUID
    is_owner: bool
    member: CompanyMember | None = None
    permissions: frozenset[str] = field(default_factory=frozenset)

    def has_permission(self, code: str) -> bool:
        if self.is_owner:
            return True
        return code in self.permissions


def set_tenant_context(ctx: TenantContext) -> None:
    _current_tenant.set(ctx)


def get_tenant_context() -> TenantContext | None:
    return _current_tenant.get()


def require_tenant_context() -> TenantContext:
    ctx = get_tenant_context()
    if ctx is None:
        raise RuntimeError("Контекст компании не установлен")
    return ctx
