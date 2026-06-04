from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class ClosingDocsSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "closing_docs_sets"

    closing_docs_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    docs_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (Index("ix_closing_docs_sets_deal_id", "deal_id"),)


class ClosingDocsRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "closing_docs_records"

    closing_docs_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    closing_docs_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("closing_docs_sets.closing_docs_set_id"),
        nullable=False,
    )
    docs_manifest_json: Mapped[str] = mapped_column(Text, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (Index("ix_closing_docs_records_set_id", "closing_docs_set_id"),)


class ClosingDocsItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "closing_docs_items"

    closing_docs_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("closing_docs_records.closing_docs_id"),
        nullable=False,
    )
    item_code: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    item_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_closing_docs_items_docs_id", "closing_docs_id"),
        Index("ix_closing_docs_items_item_code", "item_code"),
    )


class ClosingDocsFlag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "closing_docs_flags"

    closing_docs_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("closing_docs_records.closing_docs_id"),
        nullable=False,
    )
    flag_code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_closing_docs_flags_docs_id", "closing_docs_id"),
        Index("ix_closing_docs_flags_flag_code", "flag_code"),
    )
