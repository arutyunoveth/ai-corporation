from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class SubmissionReceiptSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "submission_receipt_sets"

    submission_receipt_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    submission_execution_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("submission_execution_sets.submission_execution_set_id"),
        nullable=False,
    )
    receipt_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_submission_receipt_sets_deal_id", "deal_id"),
        Index("ix_submission_receipt_sets_execution_set_id", "submission_execution_set_id"),
    )


class SubmissionReceiptRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "submission_receipt_records"

    submission_receipt_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    submission_receipt_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("submission_receipt_sets.submission_receipt_set_id"),
        nullable=False,
    )
    receipt_number: Mapped[str] = mapped_column(String(128), nullable=False)
    receipt_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    receipt_source: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_submission_receipt_records_set_id", "submission_receipt_set_id"),
        Index("ix_submission_receipt_records_receipt_number", "receipt_number"),
    )


class SubmissionReceiptBinding(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "submission_receipt_bindings"

    submission_receipt_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("submission_receipt_records.submission_receipt_id"),
        nullable=False,
    )
    artifact_ref: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("document_artifacts.artifact_ref"),
        nullable=False,
    )
    binding_type: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_submission_receipt_bindings_submission_receipt_id", "submission_receipt_id"),
        Index("ix_submission_receipt_bindings_artifact_ref", "artifact_ref"),
    )
