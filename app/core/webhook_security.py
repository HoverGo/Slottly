"""Проверка подлинности webhook платёжного провайдера"""

import secrets

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.models.enums import PaymentProvider


def verify_payment_webhook(request: Request, provider: PaymentProvider) -> None:
    if provider == PaymentProvider.MOCK and settings.environment == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mock-провайдер недоступен в production",
        )

    secret = settings.payment_webhook_secret
    if not secret:
        if settings.environment == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Webhook secret не настроен",
            )
        return

    header = request.headers.get("X-Webhook-Secret") or request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        header = header[7:].strip()

    if not secrets.compare_digest(header, secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный webhook secret",
        )
