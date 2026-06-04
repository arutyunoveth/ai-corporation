from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class LogisticsTrackingSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "logistics_tracking_sets"

    logistics_tracking_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    logistics_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (Index("ix_logistics_tracking_sets_deal_id", "deal_id"),)


class LogisticsTrackingRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "logistics_tracking_records"

    logistics_tracking_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    logistics_tracking_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("logistics_tracking_sets.logistics_tracking_set_id"),
        nullable=False,
    )
    eta_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (Index("ix_logistics_tracking_records_set_id", "logistics_tracking_set_id"),)


class LogisticsTrackingEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "logistics_tracking_events"

    logistics_tracking_event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    logistics_tracking_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("logistics_tracking_records.logistics_tracking_id"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_logistics_tracking_events_tracking_id", "logistics_tracking_id"),
        Index("ix_logistics_tracking_events_event_timestamp", "event_timestamp"),
    )


class LogisticsTrackingLink(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "logistics_tracking_links"

    logistics_tracking_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("logistics_tracking_records.logistics_tracking_id"),
        nullable=False,
    )
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (Index("ix_logistics_tracking_links_tracking_id", "logistics_tracking_id"),)
