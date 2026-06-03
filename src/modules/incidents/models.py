from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class IncidentSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "incident_sets"

    incident_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    execution_command_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("execution_command_sets.execution_command_set_id"),
        nullable=False,
    )
    incident_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_incident_sets_deal_id", "deal_id"),
        Index("ix_incident_sets_execution_command_set_id", "execution_command_set_id"),
    )


class IncidentRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "incident_records"

    incident_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    incident_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("incident_sets.incident_set_id"),
        nullable=False,
    )
    incident_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_incident_records_set_id", "incident_set_id"),
        Index("ix_incident_records_incident_type", "incident_type"),
    )


class EscalationRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "escalation_records"

    escalation_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    incident_id: Mapped[str] = mapped_column(String(64), ForeignKey("incident_records.incident_id"), nullable=False)
    escalation_level: Mapped[str] = mapped_column(Text, nullable=False)
    escalation_status: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_escalation_records_incident_id", "incident_id"),
        Index("ix_escalation_records_escalation_level", "escalation_level"),
    )
