from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class ExecutionLedgerSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "execution_ledger_sets"

    execution_ledger_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    ledger_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_execution_ledger_sets_scope_type", "scope_type"),
        Index("ix_execution_ledger_sets_scope_ref", "scope_ref"),
    )


class ExecutionLedgerRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "execution_ledger_records"

    execution_ledger_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    execution_ledger_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("execution_ledger_sets.execution_ledger_set_id"),
        nullable=False,
    )
    action_queue_id: Mapped[str] = mapped_column(String(64), nullable=False)
    integration_task_id: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_status: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_execution_ledger_records_set_id", "execution_ledger_set_id"),
        Index("ix_execution_ledger_records_action_queue_id", "action_queue_id"),
        Index("ix_execution_ledger_records_integration_task_id", "integration_task_id"),
        Index("ix_execution_ledger_records_execution_status", "execution_status"),
    )


class ExecutionResultRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "execution_result_records"

    execution_ledger_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("execution_ledger_records.execution_ledger_id"),
        nullable=False,
    )
    result_code: Mapped[str] = mapped_column(String(64), nullable=False)
    result_summary: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_execution_result_records_execution_ledger_id", "execution_ledger_id"),
        Index("ix_execution_result_records_result_code", "result_code"),
    )
