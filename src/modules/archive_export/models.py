from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class ArchiveExportSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "archive_export_sets"

    archive_export_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    deal_closure_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("deal_closure_sets.deal_closure_set_id"),
        nullable=False,
    )
    export_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_archive_export_sets_deal_id", "deal_id"),
        Index("ix_archive_export_sets_deal_closure_set_id", "deal_closure_set_id"),
    )


class ArchiveExportRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "archive_export_records"

    archive_export_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    archive_export_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("archive_export_sets.archive_export_set_id"),
        nullable=False,
    )
    export_manifest_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    export_format: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_archive_export_records_set_id", "archive_export_set_id"),
    )


class ArchiveExportItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "archive_export_items"

    archive_export_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("archive_export_records.archive_export_id"),
        nullable=False,
    )
    artifact_ref: Mapped[str] = mapped_column(String(64), ForeignKey("document_artifacts.artifact_ref"), nullable=False)
    item_role: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_archive_export_items_archive_export_id", "archive_export_id"),
        Index("ix_archive_export_items_artifact_ref", "artifact_ref"),
    )
