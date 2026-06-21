from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID


@dataclass
class CheckoutResult:
    provider_payment_id: str
    confirmation_url: str | None
    metadata: dict[str, Any] | None = None


class PaymentProviderGateway(Protocol):
    async def create_checkout(
        self,
        *,
        payment_id: UUID,
        amount: int,
        currency: str,
        description: str,
        return_url: str | None,
    ) -> CheckoutResult: ...

    async def parse_webhook(self, payload: dict[str, Any]) -> tuple[str, str]: ...
