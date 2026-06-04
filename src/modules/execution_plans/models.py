from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class ExecutionPlanSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "execution_plan_sets"

    execution_plan_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    plan_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_execution_plan_sets_deal_id", "deal_id"),
    )


class ExecutionPlanRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "execution_plan_records"

    execution_plan_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    execution_plan_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("execution_plan_sets.execution_plan_set_id"),
        nullable=False,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    baseline_manifest_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_execution_plan_records_set_id", "execution_plan_set_id"),
    )


class ExecutionPlanMilestone(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "execution_plan_milestones"

    execution_plan_milestone_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    execution_plan_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("execution_plan_records.execution_plan_id"),
        nullable=False,
    )
    milestone_code: Mapped[str] = mapped_column(String(64), nullable=False)
    milestone_name: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    milestone_state: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_execution_plan_milestones_plan_id", "execution_plan_id"),
        Index("ix_execution_plan_milestones_milestone_code", "milestone_code"),
    )


class ExecutionPlanAssumption(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "execution_plan_assumptions"

    execution_plan_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("execution_plan_records.execution_plan_id"),
        nullable=False,
    )
    assumption_code: Mapped[str] = mapped_column(String(64), nullable=False)
    assumption_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_execution_plan_assumptions_plan_id", "execution_plan_id"),
        Index("ix_execution_plan_assumptions_code", "assumption_code"),
    )
