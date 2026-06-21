from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRET_KEYS = frozenset(
    {
        "change-me-to-a-random-secret-key",
        "secret",
        "changeme",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/commerce_db"
    secret_key: str = "change-me-to-a-random-secret-key"
    access_token_expire_minutes: int = 60
    debug: bool = False
    environment: str = "development"
    algorithm: str = "HS256"
    payment_provider: str = "mock"
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    platform_admin_emails: str = ""
    platform_support_emails: str = ""
    payment_return_url: str = "http://localhost:8000/cabinet/payments/success"
    payment_webhook_secret: str = ""
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 5
    max_request_body_mb: int = 10
    media_url_prefix: str = "/api/v1/media"
    invite_base_url: str = "http://localhost:8000/invite"
    invite_token_expire_days: int = 7
    public_booking_base_url: str = "http://localhost:8000/book"

    cors_origins: str = ""
    trusted_hosts: str = ""
    trust_proxy_headers: bool = False

    redis_url: str = ""
    rate_limit_enabled: bool = True
    brute_force_enabled: bool = True
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15
    login_attempt_window_minutes: int = 15
    audit_enabled: bool = True

    openapi_enabled: bool | None = True

    @property
    def platform_admin_emails_list(self) -> list[str]:
        return [email.strip().lower() for email in self.platform_admin_emails.split(",") if email.strip()]

    @property
    def platform_support_emails_list(self) -> list[str]:
        return [email.strip().lower() for email in self.platform_support_emails.split(",") if email.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def trusted_hosts_list(self) -> list[str]:
        return [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def docs_enabled(self) -> bool:
        if self.openapi_enabled is not None:
            return self.openapi_enabled
        return not self.is_production and self.debug

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if not self.is_production:
            return self
        errors: list[str] = []
        if self.secret_key in INSECURE_SECRET_KEYS or len(self.secret_key) < 32:
            errors.append("SECRET_KEY: задайте случайную строку не короче 32 символов")
        if "postgres:postgres@" in self.database_url:
            errors.append("DATABASE_URL: не используйте пароль postgres/postgres в production")
        if self.payment_provider == "mock":
            errors.append("PAYMENT_PROVIDER: mock недопустим в production")
        if not self.payment_webhook_secret:
            errors.append("PAYMENT_WEBHOOK_SECRET: обязателен в production")
        if self.debug:
            errors.append("DEBUG: должен быть false в production")
        if errors:
            raise ValueError("Небезопасная конфигурация production: " + "; ".join(errors))
        return self


settings = Settings()
