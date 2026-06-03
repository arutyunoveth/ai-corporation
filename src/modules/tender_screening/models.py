from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class TenderScreeningRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tender_screening_records"

    screening_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    intake_id: Mapped[str] = mapped_column(String(64), ForeignKey("tender_intake_records.intake_id"), nullable=False)
    document_set_id: Mapped[str] = mapped_column(String(64), ForeignKey("document_sets.document_set_id"), nullable=False)
    tender_summary_id: Mapped[str] = mapped_column(String(64), ForeignKey("tender_summaries.tender_summary_id"), nullable=False)
    result_status: Mapped[str] = mapped_column(Text, nullable=False)
    screening_score: Mapped[float] = mapped_column(nullable=False)
    rationale_text: Mapped[str] = mapped_column(Text, nullable=False)
    factor_breakdown_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    reason_codes_json: Mapped[list] = mapped_column(JSON, nullable=False)
    recommended_next_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_tender_screening_records_deal_id", "deal_id"),
        Index("ix_tender_screening_records_intake_id", "intake_id"),
        Index("ix_tender_screening_records_result_status", "result_status"),
    )

