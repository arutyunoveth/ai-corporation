from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class SupplierFulfillmentSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_fulfillment_sets"

    supplier_fulfillment_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    execution_command_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("execution_command_sets.execution_command_set_id"),
        nullable=False,
    )
    fulfillment_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_fulfillment_sets_deal_id", "deal_id"),
        Index("ix_supplier_fulfillment_sets_execution_command_set_id", "execution_command_set_id"),
    )


class SupplierFulfillmentRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_fulfillment_records"

    supplier_fulfillment_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    supplier_fulfillment_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_fulfillment_sets.supplier_fulfillment_set_id"),
        nullable=False,
    )
    supplier_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_profiles.supplier_id"),
        nullable=False,
    )
    fulfillment_state: Mapped[str] = mapped_column(Text, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_fulfillment_records_set_id", "supplier_fulfillment_set_id"),
        Index("ix_supplier_fulfillment_records_supplier_id", "supplier_id"),
    )


class SupplierFulfillmentEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_fulfillment_events"

    supplier_fulfillment_event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    supplier_fulfillment_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_fulfillment_records.supplier_fulfillment_id"),
        nullable=False,
    )
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_fulfillment_events_supplier_fulfillment_id", "supplier_fulfillment_id"),
        Index("ix_supplier_fulfillment_events_event_timestamp", "event_timestamp"),
    )
