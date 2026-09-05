"""Persist scenario-level monthly recruiting capacity.

Revision ID: m2_0002
Revises: m2_0001
Create Date: 2026-09-05
"""

from alembic import op
import sqlalchemy as sa


revision = "m2_0002"
down_revision = "m2_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scenarios",
        sa.Column("recruiting_capacity", sa.JSON(), nullable=True),
    )
    op.execute("UPDATE scenarios SET recruiting_capacity = '[2, 2, 2, 2, 2, 2]'::json")
    op.alter_column("scenarios", "recruiting_capacity", nullable=False)


def downgrade() -> None:
    op.drop_column("scenarios", "recruiting_capacity")
