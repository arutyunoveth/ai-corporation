from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class DeliveryLaunchSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "delivery_launch_sets"

    delivery_launch_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    outcome_intake_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("outcome_intake_sets.outcome_intake_set_id"),
        nullable=False,
    )
    launch_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_delivery_launch_sets_deal_id", "deal_id"),
        Index("ix_delivery_launch_sets_outcome_intake_set_id", "outcome_intake_set_id"),
    )


class DeliveryLaunchRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "delivery_launch_records"

    delivery_launch_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    delivery_launch_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("delivery_launch_sets.delivery_launch_set_id"),
        nullable=False,
    )
    launch_recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_delivery_launch_records_set_id", "delivery_launch_set_id"),
    )


class DeliveryLaunchFlag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "delivery_launch_flags"

    delivery_launch_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("delivery_launch_records.delivery_launch_id"),
        nullable=False,
    )
    flag_code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_delivery_launch_flags_delivery_launch_id", "delivery_launch_id"),
        Index("ix_delivery_launch_flags_severity", "severity"),
    )
