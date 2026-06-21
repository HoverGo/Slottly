"""Middleware аудита HTTP-запросов"""

from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.database import async_session_factory
from app.core.security import decode_access_token
from app.services.audit_service import record_http_audit, should_audit_request


def _actor_from_request(request: Request) -> UUID | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    user_id = decode_access_token(auth[7:])
    if not user_id:
        return None
    try:
        return UUID(user_id)
    except ValueError:
        return None


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if not should_audit_request(request):
            return response
        try:
            actor_user_id = _actor_from_request(request)
            async with async_session_factory() as session:
                await record_http_audit(
                    session,
                    request,
                    status_code=response.status_code,
                    actor_user_id=actor_user_id,
                )
                await session.commit()
        except Exception:
            # Аудит не должен ломать основной запрос
            pass
        return response
