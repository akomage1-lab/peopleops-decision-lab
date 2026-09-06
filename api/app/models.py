"""Aggregate scenario, historical-fact, and planning-assumption persistence models."""

from __future__ import annotations

from datetime import date
from typing import List

from sqlalchemy import CheckConstraint, Date, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class DepartmentRecord(Base):
    """A named aggregate department; no organization or user data is modeled."""

    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    roles: Mapped[List["WorkforceRoleRecord"]] = relationship(
        back_populates="department", cascade="all, delete-orphan", order_by="WorkforceRoleRecord.id"
    )


class WorkforceRoleRecord(Base):
    """A department-owned aggregate role and its planning cost assumption."""

    __tablename__ = "workforce_roles"
    __table_args__ = (
        UniqueConstraint("department_id", "name", name="uq_workforce_role_department_name"),
        CheckConstraint("monthly_loaded_cost >= 0", name="ck_workforce_role_cost_nonnegative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    monthly_loaded_cost: Mapped[float] = mapped_column(Float, nullable=False)
    department: Mapped[DepartmentRecord] = relationship(back_populates="roles")
    monthly_facts: Mapped[List["WorkforceMonthlyFactRecord"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    planning_assumptions: Mapped[List["PlanningMonthlyAssumptionRecord"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    completed_hiring_cycles: Mapped[List["CompletedHiringCycleRecord"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )


class WorkforceMonthlyFactRecord(Base):
    """Observed end-of-month aggregate FTE, hires, and exits."""

    __tablename__ = "workforce_monthly_facts"
    __table_args__ = (
        UniqueConstraint("role_id", "month", name="uq_workforce_fact_role_month"),
        CheckConstraint("observed_fte >= 0", name="ck_workforce_fact_fte_nonnegative"),
        CheckConstraint("hires >= 0", name="ck_workforce_fact_hires_nonnegative"),
        CheckConstraint("exits >= 0", name="ck_workforce_fact_exits_nonnegative"),
        CheckConstraint("EXTRACT(DAY FROM month) = 1", name="ck_workforce_fact_month_start"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("workforce_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    month: Mapped[date] = mapped_column(Date, nullable=False)
    observed_fte: Mapped[float] = mapped_column(Float, nullable=False)
    hires: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    role: Mapped[WorkforceRoleRecord] = relationship(back_populates="monthly_facts")


class PlanningMonthlyAssumptionRecord(Base):
    """Manager-entered future target and in-flight arrival assumptions, not facts."""

    __tablename__ = "planning_monthly_assumptions"
    __table_args__ = (
        UniqueConstraint("role_id", "month", name="uq_planning_assumption_role_month"),
        CheckConstraint("staffing_target >= 0", name="ck_planning_target_nonnegative"),
        CheckConstraint("in_flight_hires >= 0", name="ck_planning_inflight_nonnegative"),
        CheckConstraint("EXTRACT(DAY FROM month) = 1", name="ck_planning_assumption_month_start"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("workforce_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    month: Mapped[date] = mapped_column(Date, nullable=False)
    staffing_target: Mapped[float] = mapped_column(Float, nullable=False)
    in_flight_hires: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    role: Mapped[WorkforceRoleRecord] = relationship(back_populates="planning_assumptions")


class CompletedHiringCycleRecord(Base):
    """Anonymous completed hiring-cycle timing; it contains no candidate or employee identity."""

    __tablename__ = "completed_hiring_cycles"
    __table_args__ = (
        CheckConstraint("started_on >= opened_on", name="ck_hiring_cycle_dates_ordered"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("workforce_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opened_on: Mapped[date] = mapped_column(Date, nullable=False)
    started_on: Mapped[date] = mapped_column(Date, nullable=False)
    role: Mapped[WorkforceRoleRecord] = relationship(back_populates="completed_hiring_cycles")


class ScenarioRecord(Base):
    """Persisted aggregate planning scenario; M2 intentionally supports one seed."""

    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    planning_horizon_months: Mapped[int] = mapped_column(Integer, nullable=False)
    planning_period_incremental_workforce_budget: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    recruiting_capacity: Mapped[list] = mapped_column(JSON, nullable=False)
    roles: Mapped[List["ScenarioRoleRecord"]] = relationship(
        back_populates="scenario", cascade="all, delete-orphan", order_by="ScenarioRoleRecord.id"
    )


class ScenarioRoleRecord(Base):
    """All M1 inputs for one department × role, stored without employee data."""

    __tablename__ = "scenario_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(
        ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    department: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(200), nullable=False)
    current_fte: Mapped[float] = mapped_column(Float, nullable=False)
    annual_attrition_rate: Mapped[float] = mapped_column(Float, nullable=False)
    staffing_targets: Mapped[list] = mapped_column(JSON, nullable=False)
    hiring_lead_time: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_loaded_cost: Mapped[float] = mapped_column(Float, nullable=False)
    in_flight_hires: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    scenario: Mapped[ScenarioRecord] = relationship(back_populates="roles")
