import pytest
from starlette.requests import Request

from app.core.config import settings
from app.core.webhook_security import verify_payment_webhook
from app.models.enums import PaymentProvider
from fastapi import HTTPException


def _request(secret_header: str | None = None) -> Request:
    headers = []
    if secret_header is not None:
        headers.append((b"x-webhook-secret", secret_header.encode()))
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/payments/webhook/mock",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "scheme": "http",
        "query_string": b"",
        "root_path": "",
    }
    return Request(scope)


def test_webhook_rejects_wrong_secret(monkeypatch):
    monkeypatch.setattr(settings, "payment_webhook_secret", "super-secret")
    with pytest.raises(HTTPException) as exc:
        verify_payment_webhook(_request("wrong"), PaymentProvider.MOCK)
    assert exc.value.status_code == 401


def test_webhook_accepts_valid_secret(monkeypatch):
    monkeypatch.setattr(settings, "payment_webhook_secret", "super-secret")
    verify_payment_webhook(_request("super-secret"), PaymentProvider.MOCK)


def test_mock_blocked_in_production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "payment_webhook_secret", "secret")
    with pytest.raises(HTTPException) as exc:
        verify_payment_webhook(_request("secret"), PaymentProvider.MOCK)
    assert exc.value.status_code == 403
