from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class PriorityScoreRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "priority_score_records"

    priority_score_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    intake_id: Mapped[str] = mapped_column(String(64), ForeignKey("tender_intake_records.intake_id"), nullable=False)
    document_set_id: Mapped[str] = mapped_column(String(64), ForeignKey("document_sets.document_set_id"), nullable=False)
    tender_summary_id: Mapped[str] = mapped_column(String(64), ForeignKey("tender_summaries.tender_summary_id"), nullable=False)
    screening_id: Mapped[str] = mapped_column(String(64), ForeignKey("tender_screening_records.screening_id"), nullable=False)
    priority_score: Mapped[float] = mapped_column(nullable=False)
    priority_bucket: Mapped[str] = mapped_column(Text, nullable=False)
    rationale_text: Mapped[str] = mapped_column(Text, nullable=False)
    factor_breakdown_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_priority_score_records_deal_id", "deal_id"),
        Index("ix_priority_score_records_screening_id", "screening_id"),
        Index("ix_priority_score_records_priority_bucket", "priority_bucket"),
    )

