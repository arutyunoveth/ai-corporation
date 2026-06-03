from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class DealClosureSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "deal_closure_sets"

    deal_closure_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    outcome_intake_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("outcome_intake_sets.outcome_intake_set_id"),
        nullable=False,
    )
    execution_command_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("execution_command_sets.execution_command_set_id"),
        nullable=False,
    )
    closure_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_deal_closure_sets_deal_id", "deal_id"),
        Index("ix_deal_closure_sets_outcome_intake_set_id", "outcome_intake_set_id"),
        Index("ix_deal_closure_sets_execution_command_set_id", "execution_command_set_id"),
    )


class DealClosureRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "deal_closure_records"

    deal_closure_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_closure_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("deal_closure_sets.deal_closure_set_id"),
        nullable=False,
    )
    closure_code: Mapped[str] = mapped_column(Text, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_deal_closure_records_set_id", "deal_closure_set_id"),
        Index("ix_deal_closure_records_closed_at", "closed_at"),
    )


class DealArchiveSnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "deal_archive_snapshots"

    archive_snapshot_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_closure_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("deal_closure_sets.deal_closure_set_id"),
        nullable=False,
    )
    snapshot_manifest_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_deal_archive_snapshots_set_id", "deal_closure_set_id"),
    )
