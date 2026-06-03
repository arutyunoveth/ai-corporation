from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class OutcomeIntakeSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "outcome_intake_sets"

    outcome_intake_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    post_submission_tracker_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("post_submission_tracker_sets.post_submission_tracker_set_id"),
        nullable=False,
    )
    outcome_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_outcome_intake_sets_deal_id", "deal_id"),
        Index("ix_outcome_intake_sets_tracker_set_id", "post_submission_tracker_set_id"),
    )


class OutcomeIntakeRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "outcome_intake_records"

    outcome_intake_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    outcome_intake_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("outcome_intake_sets.outcome_intake_set_id"),
        nullable=False,
    )
    outcome_code: Mapped[str] = mapped_column(Text, nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_outcome_intake_records_set_id", "outcome_intake_set_id"),
        Index("ix_outcome_intake_records_effective_at", "effective_at"),
    )


class OutcomeIntakeBinding(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "outcome_intake_bindings"

    outcome_intake_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("outcome_intake_records.outcome_intake_id"),
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
        Index("ix_outcome_intake_bindings_outcome_intake_id", "outcome_intake_id"),
        Index("ix_outcome_intake_bindings_artifact_ref", "artifact_ref"),
    )
