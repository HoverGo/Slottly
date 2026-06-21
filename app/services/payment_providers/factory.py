from app.core.config import settings
from app.models.enums import PaymentProvider
from app.services.payment_providers.base import PaymentProviderGateway
from app.services.payment_providers.mock import MockPaymentProvider
from app.services.payment_providers.yookassa import YooKassaPaymentProvider


def get_payment_provider() -> PaymentProviderGateway:
    provider = PaymentProvider(settings.payment_provider)
    if provider == PaymentProvider.YOOKASSA:
        if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
            raise RuntimeError("ЮKassa не настроена")
        return YooKassaPaymentProvider(settings.yookassa_shop_id, settings.yookassa_secret_key)
    return MockPaymentProvider()
