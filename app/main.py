from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import admin, admin_company_offers, admin_support, announcements, auth, cabinet, companies, dashboard, media, payments, permissions, public_booking, public_media, reviews, schedules, services, support, warehouse
from app.core.config import settings
from app.core.database import async_session_factory
from app.core.exceptions import AppError
from app.core.redis_client import close_redis
from app.middleware.audit import AuditMiddleware
from app.middleware.security import (
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.services.seed_service import (
    ensure_basic_subscriptions_for_users,
    promote_platform_admins,
    promote_platform_support,
    seed_subscription_plans,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with async_session_factory() as session:
        await seed_subscription_plans(session)
        await promote_platform_admins(session)
        await promote_platform_support(session)
        await ensure_basic_subscriptions_for_users(session)
        await session.commit()
    yield
    await close_redis()


def create_app() -> FastAPI:
    application = FastAPI(
        title="Commerce Booking API",
        description="API системы записи с компаниями, ролями, филиалами и подписками",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    application.add_middleware(RequestSizeLimitMiddleware)
    application.add_middleware(RateLimitMiddleware)
    application.add_middleware(AuditMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)

    if settings.cors_origins_list:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Webhook-Secret"],
            max_age=600,
        )

    if settings.trusted_hosts_list:
        application.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.trusted_hosts_list,
        )

    @application.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    application.include_router(auth.router, prefix="/api/v1")
    application.include_router(admin.router, prefix="/api/v1")
    application.include_router(admin_company_offers.router, prefix="/api/v1")
    application.include_router(announcements.router, prefix="/api/v1")
    application.include_router(admin_support.router, prefix="/api/v1")
    application.include_router(support.router, prefix="/api/v1")
    application.include_router(cabinet.router, prefix="/api/v1")
    application.include_router(payments.router, prefix="/api/v1")
    application.include_router(permissions.router, prefix="/api/v1")
    application.include_router(companies.router, prefix="/api/v1")
    application.include_router(media.router, prefix="/api/v1")
    application.include_router(services.router, prefix="/api/v1")
    application.include_router(schedules.router, prefix="/api/v1")
    application.include_router(public_booking.router, prefix="/api/v1")
    application.include_router(public_media.router, prefix="/api/v1")
    application.include_router(warehouse.router, prefix="/api/v1")
    application.include_router(reviews.router, prefix="/api/v1")
    application.include_router(dashboard.router, prefix="/api/v1")

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
