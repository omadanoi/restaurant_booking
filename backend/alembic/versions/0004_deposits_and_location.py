"""booking deposits + restaurant map coordinates

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEPOSIT_STATUS = postgresql.ENUM(
    "none",
    "pending",
    "paid",
    "refunded",
    "forfeited",
    name="deposit_status",
    create_type=False,
)

PAYMENT_KIND = postgresql.ENUM("charge", "refund", name="payment_kind", create_type=False)

PAYMENT_STATUS = postgresql.ENUM("succeeded", "failed", name="payment_status", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    DEPOSIT_STATUS.create(bind, checkfirst=True)
    PAYMENT_KIND.create(bind, checkfirst=True)
    PAYMENT_STATUS.create(bind, checkfirst=True)

    # Restaurant: deposit policy + manager-set map pin.
    op.add_column(
        "restaurants",
        sa.Column("deposit_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("restaurants", sa.Column("deposit_amount", sa.Numeric(10, 2), nullable=True))
    op.add_column(
        "restaurants",
        sa.Column("deposit_currency", sa.String(length=3), server_default="USD", nullable=False),
    )
    op.add_column("restaurants", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("restaurants", sa.Column("longitude", sa.Float(), nullable=True))

    # Reservation: deposit snapshot (server_default backfills existing rows).
    op.add_column("reservations", sa.Column("deposit_amount", sa.Numeric(10, 2), nullable=True))
    op.add_column(
        "reservations", sa.Column("deposit_currency", sa.String(length=3), nullable=True)
    )
    op.add_column(
        "reservations",
        sa.Column("deposit_status", DEPOSIT_STATUS, server_default="none", nullable=False),
    )

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", PAYMENT_KIND, nullable=False),
        sa.Column("status", PAYMENT_STATUS, nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_txn_id", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(
            ["reservation_id"],
            ["reservations.id"],
            name="fk_payments_reservation_id_reservations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
    )
    op.create_index("ix_payments_reservation_id", "payments", ["reservation_id"], unique=False)


def downgrade() -> None:
    op.drop_table("payments")

    op.drop_column("reservations", "deposit_status")
    op.drop_column("reservations", "deposit_currency")
    op.drop_column("reservations", "deposit_amount")

    op.drop_column("restaurants", "longitude")
    op.drop_column("restaurants", "latitude")
    op.drop_column("restaurants", "deposit_currency")
    op.drop_column("restaurants", "deposit_amount")
    op.drop_column("restaurants", "deposit_enabled")

    bind = op.get_bind()
    PAYMENT_STATUS.drop(bind, checkfirst=True)
    PAYMENT_KIND.drop(bind, checkfirst=True)
    DEPOSIT_STATUS.drop(bind, checkfirst=True)
