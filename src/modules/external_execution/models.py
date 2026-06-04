from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class ExternalExecutionSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "external_execution_sets"

    external_execution_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    gateway_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_external_execution_sets_scope_type", "scope_type"),
        Index("ix_external_execution_sets_scope_ref", "scope_ref"),
    )


class ExternalExecutionRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "external_execution_records"

    external_execution_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    external_execution_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("external_execution_sets.external_execution_set_id"),
        nullable=False,
    )
    integration_task_id: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_ledger_id: Mapped[str] = mapped_column(String(64), nullable=False)
    gateway_action_type: Mapped[str] = mapped_column(Text, nullable=False)
    request_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    execution_status: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_external_execution_records_set_id", "external_execution_set_id"),
        Index("ix_external_execution_records_integration_task_id", "integration_task_id"),
        Index("ix_external_execution_records_execution_ledger_id", "execution_ledger_id"),
        Index("ix_external_execution_records_execution_status", "execution_status"),
    )


class ExternalExecutionResult(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "external_execution_results"

    external_execution_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("external_execution_records.external_execution_id"),
        nullable=False,
    )
    result_code: Mapped[str] = mapped_column(String(64), nullable=False)
    result_summary: Mapped[str] = mapped_column(Text, nullable=False)
    response_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    artifact_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_external_execution_results_external_execution_id", "external_execution_id"),
        Index("ix_external_execution_results_result_code", "result_code"),
    )
