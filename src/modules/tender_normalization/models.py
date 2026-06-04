from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class TenderNormalizationSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tender_normalization_sets"

    tender_normalization_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    tender_import_event_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("tender_import_events.tender_import_event_id"),
        nullable=False,
    )
    normalization_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_tender_normalization_sets_import_event_id", "tender_import_event_id"),
        Index("ix_tender_normalization_sets_status", "normalization_status"),
    )


class TenderNormalizationRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tender_normalization_records"

    tender_normalization_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    tender_normalization_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("tender_normalization_sets.tender_normalization_set_id"),
        nullable=False,
    )
    normalized_procurement_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_title: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_customer_name: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_tender_normalization_records_set_id", "tender_normalization_set_id"),
        Index("ix_tender_normalization_records_procurement_number", "normalized_procurement_number"),
    )


class TenderNormalizationLink(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tender_normalization_links"

    tender_normalization_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("tender_normalization_records.tender_normalization_id"),
        nullable=False,
    )
    customer_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("customer_profiles.customer_id"),
        nullable=True,
    )
    deal_id: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey("deals.deal_id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_tender_normalization_links_normalization_id", "tender_normalization_id"),
        Index("ix_tender_normalization_links_customer_id", "customer_id"),
        Index("ix_tender_normalization_links_deal_id", "deal_id"),
    )
