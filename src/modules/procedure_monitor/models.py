from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class ProcedureMonitorSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "procedure_monitor_sets"

    procedure_monitor_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    procedure_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_procedure_monitor_sets_deal_id", "deal_id"),
        Index("ix_procedure_monitor_sets_status", "procedure_status"),
    )


class ProcedureMonitorRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "procedure_monitor_records"

    procedure_monitor_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    procedure_monitor_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("procedure_monitor_sets.procedure_monitor_set_id"),
        nullable=False,
    )
    current_stage: Mapped[str] = mapped_column(Text, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_procedure_monitor_records_set_id", "procedure_monitor_set_id"),
    )


class ProcedureMonitorEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "procedure_monitor_events"

    procedure_event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    procedure_monitor_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("procedure_monitor_records.procedure_monitor_id"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_procedure_monitor_events_monitor_id", "procedure_monitor_id"),
        Index("ix_procedure_monitor_events_event_timestamp", "event_timestamp"),
    )


class ProcedureMonitorAlert(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "procedure_monitor_alerts"

    procedure_monitor_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("procedure_monitor_records.procedure_monitor_id"),
        nullable=False,
    )
    alert_code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_procedure_monitor_alerts_monitor_id", "procedure_monitor_id"),
        Index("ix_procedure_monitor_alerts_severity", "severity"),
    )
