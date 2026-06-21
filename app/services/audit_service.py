"""Сервис аудита действий на сервере"""

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import client_ip
from app.models.entities import AuditLog

SENSITIVE_KEYS = frozenset(
    {
        "password",
        "current_password",
        "new_password",
        "hashed_password",
        "access_token",
        "token",
        "secret",
        "payment_webhook_secret",
        "authorization",
    }
)

UUID_IN_PATH = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)

SKIP_AUDIT_PATHS = frozenset(
    {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
)

# Явные события auth пишутся в auth_service, не дублируем в middleware
AUTH_EXPLICIT_PATHS = frozenset(
    {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
    }
)


def redact_details(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            key: ("***" if key.lower() in SENSITIVE_KEYS else redact_details(value))
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [redact_details(item) for item in data]
    return data


def request_meta(request: Request) -> dict[str, str | None]:
    return {
        "ip_address": client_ip(request),
        "user_agent": (request.headers.get("user-agent") or "")[:512] or None,
        "method": request.method,
        "path": request.url.path,
    }


def extract_uuids_from_path(path: str) -> list[UUID]:
    result: list[UUID] = []
    for match in UUID_IN_PATH.findall(path):
        try:
            result.append(UUID(match))
        except ValueError:
            continue
    return result


def infer_company_id(path: str) -> UUID | None:
    marker = "/companies/"
    idx = path.find(marker)
    if idx == -1:
        return None
    rest = path[idx + len(marker) :]
    segment = rest.split("/")[0]
    try:
        return UUID(segment)
    except ValueError:
        return None


def infer_resource(path: str, method: str) -> tuple[str | None, UUID | None]:
    uuids = extract_uuids_from_path(path)
    if not uuids:
        return None, None
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 2:
        resource_type = parts[-2] if UUID_IN_PATH.fullmatch(parts[-1]) else parts[-1]
        resource_type = resource_type.replace("-", "_")
        return resource_type, uuids[-1]
    return None, uuids[-1]


def should_audit_request(request: Request) -> bool:
    from app.core.config import settings

    if not settings.audit_enabled:
        return False
    path = request.url.path
    if path in SKIP_AUDIT_PATHS:
        return False
    if not path.startswith("/api/v1"):
        return False
    if path in AUTH_EXPLICIT_PATHS:
        return False
    if path.startswith("/api/v1/admin"):
        return True
    if path.startswith("/api/v1/payments/webhook"):
        return True
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        return True
    return False


def build_http_action(request: Request) -> str:
    normalized = request.url.path.strip("/").replace("/", ".")
    return f"http.{request.method.lower()}.{normalized}"


async def record_audit_event(
    db: AsyncSession,
    *,
    action: str,
    category: str,
    success: bool = True,
    actor_user_id: UUID | None = None,
    actor_email: str | None = None,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    company_id: UUID | None = None,
    request: Request | None = None,
    status_code: int | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    meta: dict[str, str | None] = {}
    if request is not None:
        meta = request_meta(request)
        if company_id is None:
            company_id = infer_company_id(request.url.path)
        if resource_type is None and resource_id is None:
            resource_type, resource_id = infer_resource(request.url.path, request.method)

    entry = AuditLog(
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        action=action,
        category=category,
        resource_type=resource_type,
        resource_id=resource_id,
        company_id=company_id,
        ip_address=meta.get("ip_address"),
        user_agent=meta.get("user_agent"),
        method=meta.get("method"),
        path=meta.get("path"),
        status_code=status_code,
        success=success,
        details=redact_details(details) if details else None,
    )
    db.add(entry)
    await db.flush()
    return entry


async def record_http_audit(
    db: AsyncSession,
    request: Request,
    *,
    status_code: int,
    actor_user_id: UUID | None = None,
    actor_email: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    path = request.url.path
    category = "admin" if path.startswith("/api/v1/admin") else "mutation"
    if path.startswith("/api/v1/payments/webhook"):
        category = "webhook"
    success = status_code < 400
    await record_audit_event(
        db,
        action=build_http_action(request),
        category=category,
        success=success,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        request=request,
        status_code=status_code,
        details=details,
    )


async def list_audit_logs(
    db: AsyncSession,
    *,
    category: str | None = None,
    action: str | None = None,
    actor_user_id: UUID | None = None,
    company_id: UUID | None = None,
    success: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    query = select(AuditLog)
    count_query = select(func.count()).select_from(AuditLog)

    if category:
        query = query.where(AuditLog.category == category)
        count_query = count_query.where(AuditLog.category == category)
    if action:
        query = query.where(AuditLog.action.ilike(f"%{action}%"))
        count_query = count_query.where(AuditLog.action.ilike(f"%{action}%"))
    if actor_user_id:
        query = query.where(AuditLog.actor_user_id == actor_user_id)
        count_query = count_query.where(AuditLog.actor_user_id == actor_user_id)
    if company_id:
        query = query.where(AuditLog.company_id == company_id)
        count_query = count_query.where(AuditLog.company_id == company_id)
    if success is not None:
        query = query.where(AuditLog.success.is_(success))
        count_query = count_query.where(AuditLog.success.is_(success))
    if date_from:
        query = query.where(AuditLog.created_at >= date_from)
        count_query = count_query.where(AuditLog.created_at >= date_from)
    if date_to:
        query = query.where(AuditLog.created_at <= date_to)
        count_query = count_query.where(AuditLog.created_at <= date_to)

    total = (await db.execute(count_query)).scalar_one()
    rows = (
        await db.execute(
            query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()
    return list(rows), total
