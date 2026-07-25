"""Payment provider abstraction for booking deposits.

Deliberately mirrors the notification-sender strategy (ADR 0003): services
call ``get_payment_provider()`` and never know which implementation runs.

The demo provider settles synchronously, which lets the reservation service
charge inside the booking transaction — if the overlap constraint fires
after the charge, the rollback discards the payment row and no real-world
side effect exists. A REAL provider inverts this flow: the client confirms
the payment first (card entry on the provider's widget), then the booking
request carries a ``payment_token`` instead of card data, and the service
verifies/captures it. ``DepositPaymentIn`` already has room for that field;
the enum already contains the ``pending`` state an asynchronous capture
needs. Swapping providers = new class + new branch in ``provider.py`` +
setting change; zero changes at call sites.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ChargeResult:
    provider_txn_id: str


@dataclass(frozen=True)
class RefundResult:
    provider_txn_id: str


class PaymentProvider(ABC):
    name: str

    @abstractmethod
    def create_charge(
        self, *, amount: Decimal, currency: str, reservation_ref: str, card_number: str | None
    ) -> ChargeResult:
        """Charge the deposit. Raises PaymentDeclinedError on decline."""

    @abstractmethod
    def refund(self, *, provider_txn_id: str, amount: Decimal, currency: str) -> RefundResult:
        """Refund a previous charge in full."""
