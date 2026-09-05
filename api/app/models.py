"""M2 persistence models: one aggregate scenario and its role-level inputs."""

from __future__ import annotations

from typing import List

from sqlalchemy import Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


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
