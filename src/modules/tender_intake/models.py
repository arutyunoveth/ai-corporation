from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class TenderIntakeRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tender_intake_records"

    intake_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_channel: Mapped[str] = mapped_column(Text, nullable=False)
    source_title: Mapped[str] = mapped_column(Text, nullable=False)
    source_customer_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_procurement_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    intake_status: Mapped[str] = mapped_column(Text, nullable=False)
    duplicate_hint: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    normalized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_tender_intake_records_deal_id", "deal_id"),
        Index("ix_tender_intake_records_source_type", "source_type"),
        Index("ix_tender_intake_records_source_proc_number", "source_procurement_number"),
        Index("ix_tender_intake_records_received_at", "received_at"),
    )


class TenderSourcePayload(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tender_source_payloads"

    intake_id: Mapped[str] = mapped_column(String(64), ForeignKey("tender_intake_records.intake_id"), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    payload_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_tender_source_payloads_intake_id", "intake_id"),
        Index("ix_tender_source_payloads_payload_hash", "payload_hash"),
    )

