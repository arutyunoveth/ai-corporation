from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class BidPackageSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "bid_package_sets"

    bid_package_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    bid_document_collection_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("bid_document_collection_sets.bid_document_collection_set_id"),
        nullable=False,
    )
    package_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_bid_package_sets_deal_id", "deal_id"),
        Index("ix_bid_package_sets_collection_set_id", "bid_document_collection_set_id"),
    )


class BidPackageRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "bid_package_records"

    bid_package_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    bid_package_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("bid_package_sets.bid_package_set_id"),
        nullable=False,
    )
    package_version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    manifest_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_bid_package_records_set_id", "bid_package_set_id"),
    )


class BidPackageItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "bid_package_items"

    bid_package_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("bid_package_records.bid_package_id"),
        nullable=False,
    )
    artifact_ref: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("document_artifacts.artifact_ref"),
        nullable=False,
    )
    item_role: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_bid_package_items_package_id", "bid_package_id"),
        Index("ix_bid_package_items_artifact_ref", "artifact_ref"),
        Index("ix_bid_package_items_item_role", "item_role"),
    )
