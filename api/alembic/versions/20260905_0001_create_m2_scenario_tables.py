"""Create the minimal M2 aggregate planning schema.

Revision ID: m2_0001
Revises:
Create Date: 2026-09-05
"""

from alembic import op
import sqlalchemy as sa


revision = "m2_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scenarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("planning_horizon_months", sa.Integer(), nullable=False),
        sa.Column("planning_period_incremental_workforce_budget", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "scenario_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.Integer(), nullable=False),
        sa.Column("department", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=200), nullable=False),
        sa.Column("current_fte", sa.Float(), nullable=False),
        sa.Column("annual_attrition_rate", sa.Float(), nullable=False),
        sa.Column("staffing_targets", sa.JSON(), nullable=False),
        sa.Column("hiring_lead_time", sa.Integer(), nullable=False),
        sa.Column("monthly_loaded_cost", sa.Float(), nullable=False),
        sa.Column("in_flight_hires", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scenario_roles_scenario_id", "scenario_roles", ["scenario_id"])


def downgrade() -> None:
    op.drop_index("ix_scenario_roles_scenario_id", table_name="scenario_roles")
    op.drop_table("scenario_roles")
    op.drop_table("scenarios")
