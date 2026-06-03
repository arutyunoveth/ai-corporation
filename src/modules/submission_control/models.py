from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class SubmissionExecutionSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "submission_execution_sets"

    submission_execution_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    submission_readiness_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("submission_readiness_sets.submission_readiness_set_id"),
        nullable=False,
    )
    bid_package_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("bid_package_sets.bid_package_set_id"),
        nullable=False,
    )
    execution_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_submission_execution_sets_deal_id", "deal_id"),
        Index("ix_submission_execution_sets_readiness_set_id", "submission_readiness_set_id"),
        Index("ix_submission_execution_sets_bid_package_set_id", "bid_package_set_id"),
    )


class SubmissionExecutionRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "submission_execution_records"

    submission_execution_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    submission_execution_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("submission_execution_sets.submission_execution_set_id"),
        nullable=False,
    )
    channel_type: Mapped[str] = mapped_column(Text, nullable=False)
    initiated_by_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_submission_execution_records_set_id", "submission_execution_set_id"),
    )


class SubmissionAttempt(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "submission_attempts"

    submission_attempt_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    submission_execution_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("submission_execution_records.submission_execution_id"),
        nullable=False,
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_status: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_submission_attempts_submission_execution_id", "submission_execution_id"),
        Index("ix_submission_attempts_attempt_no", "attempt_no"),
    )
