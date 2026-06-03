from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class PostSubmissionTrackerSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "post_submission_tracker_sets"

    post_submission_tracker_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    submission_execution_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("submission_execution_sets.submission_execution_set_id"),
        nullable=False,
    )
    tracker_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_post_submission_tracker_sets_deal_id", "deal_id"),
        Index("ix_post_submission_tracker_sets_execution_set_id", "submission_execution_set_id"),
    )


class PostSubmissionTrackerRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "post_submission_tracker_records"

    post_submission_tracker_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    post_submission_tracker_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("post_submission_tracker_sets.post_submission_tracker_set_id"),
        nullable=False,
    )
    current_stage: Mapped[str] = mapped_column(Text, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_post_submission_tracker_records_set_id", "post_submission_tracker_set_id"),
    )


class PostSubmissionEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "post_submission_events"

    post_submission_event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    post_submission_tracker_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("post_submission_tracker_records.post_submission_tracker_id"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_post_submission_events_post_submission_tracker_id", "post_submission_tracker_id"),
        Index("ix_post_submission_events_event_timestamp", "event_timestamp"),
    )
