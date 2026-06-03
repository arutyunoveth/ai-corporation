from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class DeliveryMilestoneSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "delivery_milestone_sets"

    delivery_milestone_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    execution_command_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("execution_command_sets.execution_command_set_id"),
        nullable=False,
    )
    milestone_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_delivery_milestone_sets_deal_id", "deal_id"),
        Index("ix_delivery_milestone_sets_execution_command_set_id", "execution_command_set_id"),
    )


class DeliveryMilestoneRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "delivery_milestone_records"

    delivery_milestone_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    delivery_milestone_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("delivery_milestone_sets.delivery_milestone_set_id"),
        nullable=False,
    )
    milestone_code: Mapped[str] = mapped_column(String(64), nullable=False)
    milestone_name: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    milestone_state: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_delivery_milestone_records_set_id", "delivery_milestone_set_id"),
        Index("ix_delivery_milestone_records_milestone_code", "milestone_code"),
    )


class DeliveryMilestoneEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "delivery_milestone_events"

    delivery_milestone_event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    delivery_milestone_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("delivery_milestone_records.delivery_milestone_id"),
        nullable=False,
    )
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_delivery_milestone_events_delivery_milestone_id", "delivery_milestone_id"),
        Index("ix_delivery_milestone_events_event_timestamp", "event_timestamp"),
    )
