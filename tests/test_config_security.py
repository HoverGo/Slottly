import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_insecure_defaults():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(
            environment="production",
            secret_key="change-me-to-a-random-secret-key",
            payment_webhook_secret="webhook-secret-32-chars-minimum-xx",
            debug=False,
            payment_provider="yookassa",
        )


def test_development_allows_defaults():
    settings = Settings(environment="development")
    assert settings.environment == "development"
