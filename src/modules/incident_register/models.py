from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class IncidentRegisterSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "incident_register_sets"

    incident_register_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    incident_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (Index("ix_incident_register_sets_deal_id", "deal_id"),)


class IncidentRegisterRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "incident_register_records"

    incident_register_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    incident_register_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("incident_register_sets.incident_register_set_id"),
        nullable=False,
    )
    incident_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (Index("ix_incident_register_records_set_id", "incident_register_set_id"),)


class IncidentRegisterEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "incident_register_events"

    incident_register_event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    incident_register_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("incident_register_records.incident_register_id"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_incident_register_events_register_id", "incident_register_id"),
        Index("ix_incident_register_events_event_timestamp", "event_timestamp"),
    )


class IncidentRegisterFlag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "incident_register_flags"

    incident_register_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("incident_register_records.incident_register_id"),
        nullable=False,
    )
    flag_code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_incident_register_flags_register_id", "incident_register_id"),
        Index("ix_incident_register_flags_flag_code", "flag_code"),
    )
