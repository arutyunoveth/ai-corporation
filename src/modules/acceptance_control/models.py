from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class AcceptanceControlSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "acceptance_control_sets"

    acceptance_control_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    acceptance_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (Index("ix_acceptance_control_sets_deal_id", "deal_id"),)


class AcceptanceControlRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "acceptance_control_records"

    acceptance_control_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    acceptance_control_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("acceptance_control_sets.acceptance_control_set_id"),
        nullable=False,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_state: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (Index("ix_acceptance_control_records_set_id", "acceptance_control_set_id"),)


class AcceptanceRemark(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "acceptance_remarks"

    acceptance_control_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("acceptance_control_records.acceptance_control_id"),
        nullable=False,
    )
    remark_code: Mapped[str] = mapped_column(String(64), nullable=False)
    remark_text: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_acceptance_remarks_control_id", "acceptance_control_id"),
        Index("ix_acceptance_remarks_remark_code", "remark_code"),
    )


class AcceptanceResolutionItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "acceptance_resolution_items"

    acceptance_control_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("acceptance_control_records.acceptance_control_id"),
        nullable=False,
    )
    item_code: Mapped[str] = mapped_column(String(64), nullable=False)
    resolution_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_acceptance_resolution_items_control_id", "acceptance_control_id"),
        Index("ix_acceptance_resolution_items_item_code", "item_code"),
    )
