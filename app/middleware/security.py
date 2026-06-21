"""Security middleware: заголовки, лимиты, размер тела"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.rate_limit import enforce_rate_limit


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["X-XSS-Protection"] = "0"
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/v1/auth") else response.headers.get("Cache-Control", "")
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method != "OPTIONS":
            await enforce_rate_limit(request)
        return await call_next(request)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            max_bytes = settings.max_request_body_mb * 1024 * 1024
            if int(content_length) > max_bytes:
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Размер запроса превышает {settings.max_request_body_mb} МБ"},
                )
        return await call_next(request)
