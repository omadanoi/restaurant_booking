"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Enum types are created explicitly up front (checkfirst=True) and every
# column below is declared with create_type=False, so table creation order
# never depends on which table "first" introduces a given enum.
USER_ROLE = postgresql.ENUM(
    "customer", "waiter", "manager", "admin", name="user_role", create_type=False
)
TABLE_SHAPE = postgresql.ENUM(
    "rectangle", "circle", "square", name="table_shape", create_type=False
)
TABLE_STATUS = postgresql.ENUM(
    "available", "occupied", "reserved", "cleaning", "out_of_service",
    name="table_status", create_type=False,
)
RESERVATION_STATUS = postgresql.ENUM(
    "pending", "confirmed", "seated", "completed", "cancelled", "no_show",
    name="reservation_status", create_type=False,
)
RESERVATION_SOURCE = postgresql.ENUM(
    "online", "phone", "walk_in", name="reservation_source", create_type=False
)
NOTIFICATION_TYPE = postgresql.ENUM(
    "reservation_confirmed", "reservation_reminder", "reservation_cancelled",
    "table_ready", "waitlist_update", name="notification_type", create_type=False,
)
NOTIFICATION_CHANNEL = postgresql.ENUM(
    "email", "sms", "push", "in_app", name="notification_channel", create_type=False
)
NOTIFICATION_STATUS = postgresql.ENUM(
    "pending", "sent", "failed", name="notification_status", create_type=False
)
EMPLOYEE_ROLE_AT_RESTAURANT = postgresql.ENUM(
    "waiter", "manager", name="employee_role_at_restaurant", create_type=False
)

ALL_ENUMS = [
    USER_ROLE,
    TABLE_SHAPE,
    TABLE_STATUS,
    RESERVATION_STATUS,
    RESERVATION_SOURCE,
    NOTIFICATION_TYPE,
    NOTIFICATION_CHANNEL,
    NOTIFICATION_STATUS,
    EMPLOYEE_ROLE_AT_RESTAURANT,
]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    bind = op.get_bind()
    for enum_type in ALL_ENUMS:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("role", USER_ROLE, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"], unique=False)

    op.create_table(
        "restaurants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("country", sa.String(length=120), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("cuisine_type", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_restaurants"),
    )
    op.create_index("ix_restaurants_city", "restaurants", ["city"], unique=False)

    op.create_table(
        "floors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("restaurant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("width", sa.Float(), nullable=False),
        sa.Column("height", sa.Float(), nullable=False),
        sa.Column("background_image_url", sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(
            ["restaurant_id"], ["restaurants.id"], name="fk_floors_restaurant_id_restaurants", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_floors"),
        sa.UniqueConstraint("restaurant_id", "name", name="uq_floors_restaurant_name"),
    )

    op.create_table(
        "tables",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("restaurant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("floor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("table_number", sa.String(length=32), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("rotation", sa.Float(), nullable=False),
        sa.Column("shape", TABLE_SHAPE, nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("min_capacity", sa.Integer(), nullable=True),
        sa.Column("status", TABLE_STATUS, nullable=False),
        sa.Column("is_indoor", sa.Boolean(), nullable=False),
        sa.Column("is_accessible", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["restaurant_id"], ["restaurants.id"], name="fk_tables_restaurant_id_restaurants", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["floor_id"], ["floors.id"], name="fk_tables_floor_id_floors", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tables"),
        sa.UniqueConstraint("restaurant_id", "table_number", name="uq_tables_restaurant_number"),
    )
    op.create_index("ix_tables_restaurant_floor", "tables", ["restaurant_id", "floor_id"], unique=False)
    op.create_index("ix_tables_status", "tables", ["status"], unique=False)

    op.create_table(
        "reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("restaurant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("table_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("party_size", sa.Integer(), nullable=False),
        sa.Column("status", RESERVATION_STATUS, nullable=False),
        sa.Column("source", RESERVATION_SOURCE, nullable=False),
        sa.Column("special_requests", sa.String(length=2000), nullable=True),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["restaurant_id"], ["restaurants.id"], name="fk_reservations_restaurant_id_restaurants", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["table_id"], ["tables.id"], name="fk_reservations_table_id_tables", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["users.id"], name="fk_reservations_customer_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by"], ["users.id"], name="fk_reservations_confirmed_by_users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_reservations"),
        sa.CheckConstraint("end_time > start_time", name="ck_reservations_end_after_start"),
    )
    op.create_index("ix_reservations_customer_id", "reservations", ["customer_id"], unique=False)
    op.create_index("ix_reservations_status", "reservations", ["status"], unique=False)
    op.create_index("ix_reservations_table_start", "reservations", ["table_id", "start_time"], unique=False)
    op.create_index("ix_reservations_restaurant_start", "reservations", ["restaurant_id", "start_time"], unique=False)

    # Database-level guarantee against double-booking (ADR 0002). Requires btree_gist.
    op.execute(
        """
        ALTER TABLE reservations
        ADD CONSTRAINT ex_reservations_no_overlap
        EXCLUDE USING gist (
            table_id WITH =,
            tstzrange(start_time, end_time, '[)') WITH &&
        ) WHERE (status NOT IN ('cancelled', 'no_show'))
        """
    )

    op.create_table(
        "table_status_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("table_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("old_status", TABLE_STATUS, nullable=True),
        sa.Column("new_status", TABLE_STATUS, nullable=False),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(
            ["table_id"], ["tables.id"], name="fk_table_status_logs_table_id_tables", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["changed_by"], ["users.id"], name="fk_table_status_logs_changed_by_users", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["reservation_id"], ["reservations.id"], name="fk_table_status_logs_reservation_id_reservations", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_table_status_logs"),
    )
    op.create_index(
        "ix_table_status_logs_table_created", "table_status_logs", ["table_id", "created_at"], unique=False
    )

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("restaurant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("type", NOTIFICATION_TYPE, nullable=False),
        sa.Column("channel", NOTIFICATION_CHANNEL, nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", NOTIFICATION_STATUS, nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_notifications_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["restaurant_id"], ["restaurants.id"], name="fk_notifications_restaurant_id_restaurants", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["reservation_id"], ["reservations.id"], name="fk_notifications_reservation_id_reservations", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
    )
    op.create_index("ix_notifications_status", "notifications", ["status"], unique=False)
    op.create_index("ix_notifications_user_created", "notifications", ["user_id", "created_at"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=120), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("before", postgresql.JSONB(), nullable=True),
        sa.Column("after", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name="fk_audit_logs_actor_id_users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"], unique=False)
    op.create_index("ix_audit_logs_actor_created", "audit_logs", ["actor_id", "created_at"], unique=False)

    op.create_table(
        "opening_hours",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("restaurant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("opens_at", sa.Time(), nullable=True),
        sa.Column("closes_at", sa.Time(), nullable=True),
        sa.Column("is_closed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["restaurant_id"], ["restaurants.id"], name="fk_opening_hours_restaurant_id_restaurants", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_opening_hours"),
        sa.UniqueConstraint("restaurant_id", "day_of_week", name="uq_opening_hours_restaurant_day"),
    )

    op.create_table(
        "holidays",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("restaurant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False),
        sa.Column("opens_at", sa.Time(), nullable=True),
        sa.Column("closes_at", sa.Time(), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(
            ["restaurant_id"], ["restaurants.id"], name="fk_holidays_restaurant_id_restaurants", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_holidays"),
        sa.UniqueConstraint("restaurant_id", "date", name="uq_holidays_restaurant_date"),
    )

    op.create_table(
        "employee_restaurants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("restaurant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_at_restaurant", EMPLOYEE_ROLE_AT_RESTAURANT, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_employee_restaurants_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["restaurant_id"], ["restaurants.id"], name="fk_employee_restaurants_restaurant_id_restaurants", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_employee_restaurants"),
        sa.UniqueConstraint("user_id", "restaurant_id", name="uq_employee_restaurants_user_restaurant"),
    )


def downgrade() -> None:
    op.drop_table("employee_restaurants")
    op.drop_table("holidays")
    op.drop_table("opening_hours")
    op.drop_table("audit_logs")
    op.drop_table("notifications")
    op.drop_table("table_status_logs")
    op.drop_table("reservations")
    op.drop_table("tables")
    op.drop_table("floors")
    op.drop_table("restaurants")
    op.drop_table("users")

    bind = op.get_bind()
    for enum_type in reversed(ALL_ENUMS):
        enum_type.drop(bind, checkfirst=True)

    op.execute("DROP EXTENSION IF EXISTS btree_gist")
