from typing import Any
from uuid import UUID

from app.services.payment_providers.base import CheckoutResult, PaymentProviderGateway


class MockPaymentProvider(PaymentProviderGateway):
    """Заглушка для разработки — оплата подтверждается сразу"""

    async def create_checkout(
        self,
        *,
        payment_id: UUID,
        amount: int,
        currency: str,
        description: str,
        return_url: str | None,
    ) -> CheckoutResult:
        return CheckoutResult(
            provider_payment_id=f"mock_{payment_id}",
            confirmation_url=return_url,
            metadata={"mock": True, "auto_confirm": True},
        )

    async def parse_webhook(self, payload: dict[str, Any]) -> tuple[str, str]:
        return payload["provider_payment_id"], payload.get("status", "succeeded")
