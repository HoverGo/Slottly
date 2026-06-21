from typing import Any
from uuid import UUID

from app.services.payment_providers.base import CheckoutResult, PaymentProviderGateway


class YooKassaPaymentProvider(PaymentProviderGateway):
    """Основа интеграции с ЮKassa (онлайн-касса). Реальный API подключается позже"""

    def __init__(self, shop_id: str, secret_key: str) -> None:
        self.shop_id = shop_id
        self.secret_key = secret_key

    async def create_checkout(
        self,
        *,
        payment_id: UUID,
        amount: int,
        currency: str,
        description: str,
        return_url: str | None,
    ) -> CheckoutResult:
        # TODO: POST https://api.yookassa.ru/v3/payments
        raise NotImplementedError(
            "Интеграция с ЮKassa не настроена. Укажите YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY "
            "или используйте PAYMENT_PROVIDER=mock"
        )

    async def parse_webhook(self, payload: dict[str, Any]) -> tuple[str, str]:
        # TODO: разбор webhook notification от ЮKassa
        event = payload.get("object", {})
        return event.get("id", ""), event.get("status", "pending")
