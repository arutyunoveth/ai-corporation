from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class ShippingAcceptanceSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "shipping_acceptance_sets"

    shipping_acceptance_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    execution_command_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("execution_command_sets.execution_command_set_id"),
        nullable=False,
    )
    shipping_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_shipping_acceptance_sets_deal_id", "deal_id"),
        Index("ix_shipping_acceptance_sets_execution_command_set_id", "execution_command_set_id"),
    )


class ShippingAcceptanceRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "shipping_acceptance_records"

    shipping_acceptance_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    shipping_acceptance_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("shipping_acceptance_sets.shipping_acceptance_set_id"),
        nullable=False,
    )
    shipment_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    acceptance_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    current_state: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_shipping_acceptance_records_set_id", "shipping_acceptance_set_id"),
        Index("ix_shipping_acceptance_records_shipment_ref", "shipment_ref"),
    )


class ShippingAcceptanceEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "shipping_acceptance_events"

    shipping_acceptance_event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    shipping_acceptance_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("shipping_acceptance_records.shipping_acceptance_id"),
        nullable=False,
    )
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_shipping_acceptance_events_shipping_acceptance_id", "shipping_acceptance_id"),
        Index("ix_shipping_acceptance_events_event_timestamp", "event_timestamp"),
    )
