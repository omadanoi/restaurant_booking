from functools import lru_cache

from app.core.config import get_settings
from app.payments.base import PaymentProvider
from app.payments.demo import DemoPaymentProvider


@lru_cache
def get_payment_provider() -> PaymentProvider:
    """DI seam for payment strategies (same shape as ADR 0003).

    Adding a real provider later = new class + new branch here + setting
    change; zero changes anywhere else.
    """
    name = get_settings().PAYMENT_PROVIDER
    if name == "demo":
        return DemoPaymentProvider()
    raise ValueError(f"Unknown PAYMENT_PROVIDER: {name!r}")
