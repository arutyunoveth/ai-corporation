from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class TenderImportRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tender_import_runs"

    tender_import_run_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    run_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_tender_import_runs_source_type", "source_type"),
        Index("ix_tender_import_runs_run_status", "run_status"),
    )


class TenderImportEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tender_import_events"

    tender_import_event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    tender_import_run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("tender_import_runs.tender_import_run_id"),
        nullable=False,
    )
    raw_procurement_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_tender_import_events_run_id", "tender_import_run_id"),
        Index("ix_tender_import_events_raw_procurement_number", "raw_procurement_number"),
    )


class TenderImportPayload(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tender_import_payloads"

    tender_import_event_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("tender_import_events.tender_import_event_id"),
        nullable=False,
    )
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    payload_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_tender_import_payloads_event_id", "tender_import_event_id"),
        Index("ix_tender_import_payloads_payload_hash", "payload_hash"),
    )
