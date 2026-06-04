from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class SupplierProgressSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_progress_sets"

    supplier_progress_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(64), ForeignKey("supplier_profiles.supplier_id"), nullable=False)
    progress_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_progress_sets_deal_id", "deal_id"),
        Index("ix_supplier_progress_sets_supplier_id", "supplier_id"),
    )


class SupplierProgressRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_progress_records"

    supplier_progress_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    supplier_progress_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_progress_sets.supplier_progress_set_id"),
        nullable=False,
    )
    readiness_state: Mapped[str] = mapped_column(Text, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_progress_records_set_id", "supplier_progress_set_id"),
    )


class SupplierProgressEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_progress_events"

    supplier_progress_event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    supplier_progress_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_progress_records.supplier_progress_id"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_progress_events_progress_id", "supplier_progress_id"),
        Index("ix_supplier_progress_events_event_timestamp", "event_timestamp"),
    )


class SupplierProgressAlert(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_progress_alerts"

    supplier_progress_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_progress_records.supplier_progress_id"),
        nullable=False,
    )
    alert_code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_progress_alerts_progress_id", "supplier_progress_id"),
        Index("ix_supplier_progress_alerts_alert_code", "alert_code"),
    )
