from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class DocumentSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "document_sets"

    document_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    intake_id: Mapped[str] = mapped_column(String(64), ForeignKey("tender_intake_records.intake_id"), nullable=False)
    set_type: Mapped[str] = mapped_column(Text, nullable=False)
    ingestion_status: Mapped[str] = mapped_column(Text, nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_document_sets_deal_id", "deal_id"),
        Index("ix_document_sets_intake_id", "intake_id"),
        Index("ix_document_sets_ingestion_status", "ingestion_status"),
    )


class DocumentSetItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "document_set_items"

    document_set_id: Mapped[str] = mapped_column(String(64), ForeignKey("document_sets.document_set_id"), nullable=False)
    artifact_ref: Mapped[str] = mapped_column(String(64), ForeignKey("document_artifacts.artifact_ref"), nullable=False)
    item_role: Mapped[str] = mapped_column(Text, nullable=False)
    source_file_name: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        UniqueConstraint("document_set_id", "artifact_ref", name="uq_document_set_items_set_artifact"),
        Index("ix_document_set_items_document_set_id", "document_set_id"),
        Index("ix_document_set_items_artifact_ref", "artifact_ref"),
        Index("ix_document_set_items_item_role", "item_role"),
    )


class DocumentIngestionRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "document_ingestion_runs"

    ingestion_run_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    document_set_id: Mapped[str] = mapped_column(String(64), ForeignKey("document_sets.document_set_id"), nullable=False)
    run_status: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_document_ingestion_runs_document_set_id", "document_set_id"),
        Index("ix_document_ingestion_runs_run_status", "run_status"),
    )

