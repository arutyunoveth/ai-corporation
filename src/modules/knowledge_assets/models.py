from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class KnowledgeAssetSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "knowledge_asset_sets"

    knowledge_asset_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    postmortem_set_id: Mapped[str] = mapped_column(String(64), ForeignKey("postmortem_sets.postmortem_set_id"), nullable=False)
    archive_export_set_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("archive_export_sets.archive_export_set_id"),
        nullable=True,
    )
    dashboard_snapshot_set_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("dashboard_snapshot_sets.dashboard_snapshot_set_id"),
        nullable=True,
    )
    knowledge_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_knowledge_asset_sets_deal_id", "deal_id"),
        Index("ix_knowledge_asset_sets_postmortem_set_id", "postmortem_set_id"),
    )


class KnowledgeAssetRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "knowledge_asset_records"

    knowledge_asset_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    knowledge_asset_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_asset_sets.knowledge_asset_set_id"),
        nullable=False,
    )
    asset_title: Mapped[str] = mapped_column(Text, nullable=False)
    asset_type: Mapped[str] = mapped_column(Text, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    asset_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_knowledge_asset_records_set_id", "knowledge_asset_set_id"),
    )


class KnowledgeAssetLink(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "knowledge_asset_links"

    knowledge_asset_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_asset_records.knowledge_asset_id"),
        nullable=False,
    )
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_knowledge_asset_links_knowledge_asset_id", "knowledge_asset_id"),
    )
