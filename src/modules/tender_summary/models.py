from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class TenderSummary(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tender_summaries"

    tender_summary_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    intake_id: Mapped[str] = mapped_column(String(64), ForeignKey("tender_intake_records.intake_id"), nullable=False)
    document_set_id: Mapped[str] = mapped_column(String(64), ForeignKey("document_sets.document_set_id"), nullable=False)
    summary_status: Mapped[str] = mapped_column(Text, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_summary_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_tender_summaries_deal_id", "deal_id"),
        Index("ix_tender_summaries_intake_id", "intake_id"),
        Index("ix_tender_summaries_document_set_id", "document_set_id"),
        Index("ix_tender_summaries_summary_status", "summary_status"),
    )


class TenderSummarySourceLink(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tender_summary_source_links"

    tender_summary_id: Mapped[str] = mapped_column(String(64), ForeignKey("tender_summaries.tender_summary_id"), nullable=False)
    source_object_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_object_ref: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_tender_summary_source_links_summary_id", "tender_summary_id"),
        Index("ix_tender_summary_source_links_object", "source_object_type", "source_object_ref"),
    )
