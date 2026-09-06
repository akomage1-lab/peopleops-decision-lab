"""Add aggregate historical facts and planning-assumption foundation.

Revision ID: m3_0003
Revises: m2_0002
Create Date: 2026-09-05
"""

from alembic import op
import sqlalchemy as sa


revision = "m3_0003"
down_revision = "m2_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "workforce_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("monthly_loaded_cost", sa.Float(), nullable=False),
        sa.CheckConstraint("monthly_loaded_cost >= 0", name="ck_workforce_role_cost_nonnegative"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("department_id", "name", name="uq_workforce_role_department_name"),
    )
    op.create_index("ix_workforce_roles_department_id", "workforce_roles", ["department_id"])
    op.create_table(
        "workforce_monthly_facts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("observed_fte", sa.Float(), nullable=False),
        sa.Column("hires", sa.Integer(), nullable=False),
        sa.Column("exits", sa.Integer(), nullable=False),
        sa.CheckConstraint("observed_fte >= 0", name="ck_workforce_fact_fte_nonnegative"),
        sa.CheckConstraint("hires >= 0", name="ck_workforce_fact_hires_nonnegative"),
        sa.CheckConstraint("exits >= 0", name="ck_workforce_fact_exits_nonnegative"),
        sa.CheckConstraint("EXTRACT(DAY FROM month) = 1", name="ck_workforce_fact_month_start"),
        sa.ForeignKeyConstraint(["role_id"], ["workforce_roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "month", name="uq_workforce_fact_role_month"),
    )
    op.create_index("ix_workforce_monthly_facts_role_id", "workforce_monthly_facts", ["role_id"])
    op.create_table(
        "planning_monthly_assumptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("staffing_target", sa.Float(), nullable=False),
        sa.Column("in_flight_hires", sa.Integer(), nullable=False),
        sa.CheckConstraint("staffing_target >= 0", name="ck_planning_target_nonnegative"),
        sa.CheckConstraint("in_flight_hires >= 0", name="ck_planning_inflight_nonnegative"),
        sa.CheckConstraint("EXTRACT(DAY FROM month) = 1", name="ck_planning_assumption_month_start"),
        sa.ForeignKeyConstraint(["role_id"], ["workforce_roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "month", name="uq_planning_assumption_role_month"),
    )
    op.create_index("ix_planning_monthly_assumptions_role_id", "planning_monthly_assumptions", ["role_id"])
    op.create_table(
        "completed_hiring_cycles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("opened_on", sa.Date(), nullable=False),
        sa.Column("started_on", sa.Date(), nullable=False),
        sa.CheckConstraint("started_on >= opened_on", name="ck_hiring_cycle_dates_ordered"),
        sa.ForeignKeyConstraint(["role_id"], ["workforce_roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_completed_hiring_cycles_role_id", "completed_hiring_cycles", ["role_id"])


def downgrade() -> None:
    op.drop_index("ix_completed_hiring_cycles_role_id", table_name="completed_hiring_cycles")
    op.drop_table("completed_hiring_cycles")
    op.drop_index("ix_planning_monthly_assumptions_role_id", table_name="planning_monthly_assumptions")
    op.drop_table("planning_monthly_assumptions")
    op.drop_index("ix_workforce_monthly_facts_role_id", table_name="workforce_monthly_facts")
    op.drop_table("workforce_monthly_facts")
    op.drop_index("ix_workforce_roles_department_id", table_name="workforce_roles")
    op.drop_table("workforce_roles")
    op.drop_table("departments")
