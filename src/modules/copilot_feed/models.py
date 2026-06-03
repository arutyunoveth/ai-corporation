from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class CopilotFeedSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "copilot_feed_sets"

    copilot_feed_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    feed_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_copilot_feed_sets_scope_type", "scope_type"),
        Index("ix_copilot_feed_sets_scope_ref", "scope_ref"),
    )


class CopilotFeedRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "copilot_feed_records"

    copilot_feed_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    copilot_feed_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("copilot_feed_sets.copilot_feed_set_id"),
        nullable=False,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_copilot_feed_records_set_id", "copilot_feed_set_id"),
    )


class CopilotFeedItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "copilot_feed_items"

    copilot_feed_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("copilot_feed_records.copilot_feed_id"),
        nullable=False,
    )
    item_code: Mapped[str] = mapped_column(String(64), nullable=False)
    item_type: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(Text, nullable=False)
    item_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_copilot_feed_items_feed_id", "copilot_feed_id"),
        Index("ix_copilot_feed_items_item_type", "item_type"),
        Index("ix_copilot_feed_items_priority", "priority"),
    )
