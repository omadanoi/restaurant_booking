"""floor elements (non-bookable layout features)

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ELEMENT_TYPE = postgresql.ENUM(
    "wall",
    "door",
    "window",
    "restroom",
    "bar",
    "entrance",
    "kitchen",
    "plant",
    "label",
    name="element_type",
    create_type=False,
)


def upgrade() -> None:
    ELEMENT_TYPE.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "floor_elements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("restaurant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("floor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("element_type", ELEMENT_TYPE, nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("width", sa.Float(), nullable=False),
        sa.Column("height", sa.Float(), nullable=False),
        sa.Column("rotation", sa.Float(), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(
            ["restaurant_id"], ["restaurants.id"], name="fk_floor_elements_restaurant_id_restaurants", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["floor_id"], ["floors.id"], name="fk_floor_elements_floor_id_floors", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_floor_elements"),
    )
    op.create_index(
        "ix_floor_elements_restaurant_floor", "floor_elements", ["restaurant_id", "floor_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("floor_elements")
    ELEMENT_TYPE.drop(op.get_bind(), checkfirst=True)
