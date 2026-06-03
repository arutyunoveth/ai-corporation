from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class BidDocumentCollectionSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "bid_document_collection_sets"

    bid_document_collection_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    document_requirement_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("document_requirement_sets.document_requirement_set_id"),
        nullable=False,
    )
    ceo_approval_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("ceo_approval_sets.ceo_approval_set_id"),
        nullable=False,
    )
    collection_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_bid_document_collection_sets_deal_id", "deal_id"),
        Index("ix_bid_document_collection_sets_requirement_set_id", "document_requirement_set_id"),
    )


class BidDocumentCollectionRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "bid_document_collection_rows"

    bid_document_collection_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("bid_document_collection_sets.bid_document_collection_set_id"),
        nullable=False,
    )
    requirement_row_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_ref: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("document_artifacts.artifact_ref"),
        nullable=True,
    )
    collection_status: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_bid_document_collection_rows_set_id", "bid_document_collection_set_id"),
        Index("ix_bid_document_collection_rows_requirement_row_ref", "requirement_row_ref"),
        Index("ix_bid_document_collection_rows_collection_status", "collection_status"),
    )


class BidDocumentCollectionBinding(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "bid_document_collection_bindings"

    bid_document_collection_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("bid_document_collection_sets.bid_document_collection_set_id"),
        nullable=False,
    )
    source_object_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_object_ref: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_bid_document_collection_bindings_set_id", "bid_document_collection_set_id"),
        Index("ix_bid_document_collection_bindings_source_ref", "source_object_type", "source_object_ref"),
    )
