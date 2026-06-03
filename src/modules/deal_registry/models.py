from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class Deal(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "deals"

    deal_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    customer_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    procurement_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    procurement_channel: Mapped[str | None] = mapped_column(Text, nullable=True)
    initial_source_type: Mapped[str] = mapped_column(Text, nullable=False)
    direction_type: Mapped[str] = mapped_column(Text, nullable=False)
    domain_type: Mapped[str] = mapped_column(Text, nullable=False)
    current_status: Mapped[str] = mapped_column(Text, nullable=False)
    priority_bucket: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_deals_current_status", "current_status"),
        Index("ix_deals_created_at", "created_at"),
        Index("ix_deals_procurement_number", "procurement_number"),
    )


class DealExternalRef(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "deal_external_refs"

    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    ref_type: Mapped[str] = mapped_column(Text, nullable=False)
    ref_value: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_deal_external_refs_deal_id", "deal_id"),
        Index("ix_deal_external_refs_ref_type", "ref_type"),
    )


class DealTag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "deal_tags"

    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    tag_code: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_deal_tags_deal_id", "deal_id"),
        Index("ix_deal_tags_tag_code", "tag_code"),
    )

