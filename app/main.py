from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import admin, admin_support, auth, cabinet, companies, payments, permissions, schedules, services, support
from app.core.database import async_session_factory
from app.core.exceptions import AppError
from app.services.seed_service import promote_platform_admins, promote_platform_support, seed_subscription_plans


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with async_session_factory() as session:
        await seed_subscription_plans(session)
        await promote_platform_admins(session)
        await promote_platform_support(session)
        await session.commit()
    yield


app = FastAPI(
    title="Commerce Booking API",
    description="API системы записи с компаниями, ролями, филиалами и подписками",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(admin_support.router, prefix="/api/v1")
app.include_router(support.router, prefix="/api/v1")
app.include_router(cabinet.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(permissions.router, prefix="/api/v1")
app.include_router(companies.router, prefix="/api/v1")
app.include_router(services.router, prefix="/api/v1")
app.include_router(schedules.router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
