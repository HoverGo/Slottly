import enum


class PaymentProvider(str, enum.Enum):
    MOCK = "mock"
    YOOKASSA = "yookassa"
    CLOUDPAYMENTS = "cloudpayments"


class PaymentAction(str, enum.Enum):
    PURCHASE = "purchase"
    RENEW = "renew"
    CHANGE_PLAN = "change_plan"


VALID_BILLING_MONTHS = frozenset({1, 3, 6, 12})
