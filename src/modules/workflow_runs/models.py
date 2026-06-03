from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class WorkflowRunSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "workflow_run_sets"

    workflow_run_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    workflow_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_workflow_run_sets_scope_type", "scope_type"),
        Index("ix_workflow_run_sets_scope_ref", "scope_ref"),
    )


class WorkflowRunRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "workflow_run_records"

    workflow_run_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    workflow_run_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("workflow_run_sets.workflow_run_set_id"),
        nullable=False,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    current_phase: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_workflow_run_records_set_id", "workflow_run_set_id"),
    )


class WorkflowStepRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "workflow_step_records"

    workflow_step_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    workflow_run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("workflow_run_records.workflow_run_id"),
        nullable=False,
    )
    step_code: Mapped[str] = mapped_column(String(64), nullable=False)
    step_type: Mapped[str] = mapped_column(Text, nullable=False)
    step_status: Mapped[str] = mapped_column(Text, nullable=False)
    depends_on_step_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_workflow_step_records_run_id", "workflow_run_id"),
        Index("ix_workflow_step_records_step_code", "step_code"),
    )
