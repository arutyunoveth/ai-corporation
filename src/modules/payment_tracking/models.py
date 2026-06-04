from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class PaymentTrackingSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "payment_tracking_sets"

    payment_tracking_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    payment_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (Index("ix_payment_tracking_sets_deal_id", "deal_id"),)


class PaymentTrackingRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "payment_tracking_records"

    payment_tracking_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    payment_tracking_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("payment_tracking_sets.payment_tracking_set_id"),
        nullable=False,
    )
    expected_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    paid_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    overdue_days: Mapped[int] = mapped_column(nullable=False, default=0)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (Index("ix_payment_tracking_records_set_id", "payment_tracking_set_id"),)


class PaymentTrackingEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "payment_tracking_events"

    payment_tracking_event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    payment_tracking_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("payment_tracking_records.payment_tracking_id"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_payment_tracking_events_tracking_id", "payment_tracking_id"),
        Index("ix_payment_tracking_events_event_timestamp", "event_timestamp"),
    )


class PaymentTrackingAlert(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "payment_tracking_alerts"

    payment_tracking_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("payment_tracking_records.payment_tracking_id"),
        nullable=False,
    )
    alert_code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_payment_tracking_alerts_tracking_id", "payment_tracking_id"),
        Index("ix_payment_tracking_alerts_alert_code", "alert_code"),
    )
