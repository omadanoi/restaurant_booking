# ADR 0004: Booking deposits behind a payment-provider strategy

## Status
Accepted

## Context
No-shows and prank bookings cost restaurants real money: a held table earns nothing. The classic countermeasure is a small booking deposit — refunded on cancellation, kept on a no-show. The platform is currently a demo but is intended to launch commercially in Kyrgyzstan, where the eventual payment service provider is not yet chosen. Real payment integration requires merchant accounts and API keys that must not become a prerequisite for running or evaluating the project, and whichever provider is chosen later must plug in without rewriting booking logic.

## Decision
Mirror the notification pattern (ADR 0003): a `PaymentProvider` abstract interface (`create_charge`, `refund`) in `app/payments/base.py`, obtained through a DI factory (`get_payment_provider()`) keyed on the `PAYMENT_PROVIDER` setting. The default `DemoPaymentProvider` settles instantly in-process — no external calls — and declines any card number ending in `0002` so the failure path is exercisable in demos and tests.

Deposit *policy* lives on the restaurant (`deposit_enabled`, `deposit_amount`, `deposit_currency`, manager-editable); each reservation *snapshots* the amount at booking time so later policy changes never alter what a customer already paid. Deposit state is an explicit enum on the reservation (`none/pending/paid/refunded/forfeited`), and every money movement is recorded as a row in a `payments` table with the provider's transaction id — the audit trail a real provider will need for reconciliation.

Because the demo provider is synchronous and side-effect-free, the charge happens *inside* the booking transaction: if the overlap EXCLUDE constraint (ADR 0002) fires after the charge, the rollback discards everything, and a failed payment can never hold a table. A real provider inverts this flow — the client confirms payment first and the booking request carries a payment token; the `pending` enum state and the `DepositPaymentIn` schema already leave room for that, so the switch is additive.

Refunds are issued from a single service helper called from both cancellation paths (customer cancel and staff status change); the no-show transition flips the deposit to `forfeited` with no provider call, since the money was captured at booking.

## Consequences
- The project runs end-to-end with zero payment-provider configuration, while the full deposit lifecycle (charge, refund, forfeit, decline) is real, observable, and covered by API tests.
- Integrating the eventual Kyrgyz PSP is a new class + a factory branch + a settings change, plus swapping the synchronous charge for token verification — service call sites and schemas are untouched.
- The `payments` table decouples "what the customer owes/paid" (reservation snapshot) from "what money actually moved" (transaction rows), which is the shape disputes and reconciliation require.
- A deposit-holding reservation can never block a table without payment having succeeded, so no expiry/cleanup job is needed.
