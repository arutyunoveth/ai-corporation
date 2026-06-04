from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class LaunchVisibilitySet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "launch_visibility_sets"

    launch_visibility_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    visibility_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_launch_visibility_sets_scope_type", "scope_type"),
        Index("ix_launch_visibility_sets_scope_ref", "scope_ref"),
    )


class LaunchVisibilityRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "launch_visibility_records"

    launch_visibility_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    launch_visibility_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("launch_visibility_sets.launch_visibility_set_id"),
        nullable=False,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    active_deal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked_deal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    red_flag_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    manual_review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overdue_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (Index("ix_launch_visibility_records_set_id", "launch_visibility_set_id"),)


class LaunchVisibilityItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "launch_visibility_items"

    launch_visibility_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("launch_visibility_records.launch_visibility_id"),
        nullable=False,
    )
    deal_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=True)
    item_code: Mapped[str] = mapped_column(String(64), nullable=False)
    item_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    source_module_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    detail_text: Mapped[str] = mapped_column(Text, nullable=False)
    requires_manual_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_launch_visibility_items_visibility_id", "launch_visibility_id"),
        Index("ix_launch_visibility_items_deal_id", "deal_id"),
        Index("ix_launch_visibility_items_item_type", "item_type"),
        Index("ix_launch_visibility_items_severity", "severity"),
    )
