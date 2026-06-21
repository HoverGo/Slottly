from pydantic_settings import BaseSettings, SettingsConfigDict


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
    algorithm: str = "HS256"
    payment_provider: str = "mock"
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    platform_admin_emails: str = ""
    platform_support_emails: str = ""
    payment_return_url: str = "http://localhost:8000/cabinet/payments/success"

    @property
    def platform_admin_emails_list(self) -> list[str]:
        return [email.strip().lower() for email in self.platform_admin_emails.split(",") if email.strip()]

    @property
    def platform_support_emails_list(self) -> list[str]:
        return [email.strip().lower() for email in self.platform_support_emails.split(",") if email.strip()]


settings = Settings()
