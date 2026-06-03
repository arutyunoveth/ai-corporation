from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class SubmissionReadinessSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "submission_readiness_sets"

    submission_readiness_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    bid_completeness_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("bid_completeness_sets.bid_completeness_set_id"),
        nullable=False,
    )
    ceo_approval_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("ceo_approval_sets.ceo_approval_set_id"),
        nullable=False,
    )
    finance_memo_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("finance_memo_sets.finance_memo_set_id"),
        nullable=False,
    )
    integrated_risk_memo_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("integrated_risk_memo_sets.integrated_risk_memo_set_id"),
        nullable=False,
    )
    readiness_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_submission_readiness_sets_deal_id", "deal_id"),
        Index("ix_submission_readiness_sets_completeness_set_id", "bid_completeness_set_id"),
    )


class SubmissionReadinessRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "submission_readiness_records"

    submission_readiness_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    submission_readiness_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("submission_readiness_sets.submission_readiness_set_id"),
        nullable=False,
    )
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_submission_readiness_records_set_id", "submission_readiness_set_id"),
    )


class SubmissionReadinessFlag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "submission_readiness_flags"

    submission_readiness_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("submission_readiness_records.submission_readiness_id"),
        nullable=False,
    )
    flag_code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_submission_readiness_flags_submission_readiness_id", "submission_readiness_id"),
        Index("ix_submission_readiness_flags_severity", "severity"),
    )
