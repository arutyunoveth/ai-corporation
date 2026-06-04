from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class SubmissionArchiveSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "submission_archive_sets"

    submission_archive_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    archive_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_submission_archive_sets_deal_id", "deal_id"),
        Index("ix_submission_archive_sets_archive_status", "archive_status"),
    )


class SubmissionArchiveRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "submission_archive_records"

    submission_archive_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    submission_archive_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("submission_archive_sets.submission_archive_set_id"),
        nullable=False,
    )
    archive_manifest_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    proof_summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_submission_archive_records_set_id", "submission_archive_set_id"),
    )


class SubmissionArchiveItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "submission_archive_items"

    submission_archive_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("submission_archive_records.submission_archive_id"),
        nullable=False,
    )
    artifact_ref: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("document_artifacts.artifact_ref"),
        nullable=False,
    )
    item_role: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_submission_archive_items_submission_archive_id", "submission_archive_id"),
        Index("ix_submission_archive_items_artifact_ref", "artifact_ref"),
        Index("ix_submission_archive_items_item_role", "item_role"),
    )
