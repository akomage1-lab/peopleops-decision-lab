"""Add explicit future attrition and lead-time planning assumptions.

Revision ID: m4_0004
Revises: m3_0003
Create Date: 2026-09-05
"""

from alembic import op
import sqlalchemy as sa


revision = "m4_0004"
down_revision = "m3_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workforce_roles", sa.Column("annual_expected_attrition_rate", sa.Float(), nullable=True))
    op.add_column("workforce_roles", sa.Column("hiring_lead_time", sa.Integer(), nullable=True))
    op.execute("UPDATE workforce_roles SET annual_expected_attrition_rate = 0.08, hiring_lead_time = 1")
    op.alter_column("workforce_roles", "annual_expected_attrition_rate", nullable=False)
    op.alter_column("workforce_roles", "hiring_lead_time", nullable=False)
    op.create_check_constraint("ck_workforce_role_future_attrition", "workforce_roles", "annual_expected_attrition_rate >= 0 AND annual_expected_attrition_rate < 1")
    op.create_check_constraint("ck_workforce_role_lead_time_nonnegative", "workforce_roles", "hiring_lead_time >= 0")


def downgrade() -> None:
    op.drop_constraint("ck_workforce_role_lead_time_nonnegative", "workforce_roles", type_="check")
    op.drop_constraint("ck_workforce_role_future_attrition", "workforce_roles", type_="check")
    op.drop_column("workforce_roles", "hiring_lead_time")
    op.drop_column("workforce_roles", "annual_expected_attrition_rate")
