"""Instantly-settling fake provider for demos and tests.

Follows the Stripe test-card convention: any card number ending in 0002 is
declined, everything else succeeds. No state, no external calls.
"""

import uuid
from decimal import Decimal

from app.core.exceptions import PaymentDeclinedError
from app.core.logging import get_logger
from app.payments.base import ChargeResult, PaymentProvider, RefundResult

logger = get_logger(__name__)

DECLINE_SUFFIX = "0002"


class DemoPaymentProvider(PaymentProvider):
    name = "demo"

    def create_charge(
        self, *, amount: Decimal, currency: str, reservation_ref: str, card_number: str | None
    ) -> ChargeResult:
        digits = "".join(c for c in (card_number or "") if c.isdigit())
        if digits.endswith(DECLINE_SUFFIX):
            logger.info(
                "demo_payment_declined",
                extra={"extra_fields": {"reservation_ref": reservation_ref}},
            )
            raise PaymentDeclinedError("Card declined (demo). Try a different card number.")
        txn_id = f"demo_ch_{uuid.uuid4().hex}"
        logger.info(
            "demo_payment_charged",
            extra={
                "extra_fields": {
                    "reservation_ref": reservation_ref,
                    "amount": str(amount),
                    "currency": currency,
                    "txn_id": txn_id,
                }
            },
        )
        return ChargeResult(provider_txn_id=txn_id)

    def refund(self, *, provider_txn_id: str, amount: Decimal, currency: str) -> RefundResult:
        refund_id = f"demo_re_{uuid.uuid4().hex}"
        logger.info(
            "demo_payment_refunded",
            extra={
                "extra_fields": {
                    "charge_txn_id": provider_txn_id,
                    "amount": str(amount),
                    "currency": currency,
                    "refund_id": refund_id,
                }
            },
        )
        return RefundResult(provider_txn_id=refund_id)
