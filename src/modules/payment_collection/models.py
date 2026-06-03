from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class PaymentCollectionSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "payment_collection_sets"

    payment_collection_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    execution_command_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("execution_command_sets.execution_command_set_id"),
        nullable=False,
    )
    collection_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_payment_collection_sets_deal_id", "deal_id"),
        Index("ix_payment_collection_sets_execution_command_set_id", "execution_command_set_id"),
    )


class PaymentCollectionRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "payment_collection_records"

    payment_collection_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    payment_collection_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("payment_collection_sets.payment_collection_set_id"),
        nullable=False,
    )
    invoice_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expected_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    collected_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False, default="RUB")
    collection_state: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_payment_collection_records_set_id", "payment_collection_set_id"),
        Index("ix_payment_collection_records_invoice_ref", "invoice_ref"),
    )


class PaymentCollectionEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "payment_collection_events"

    payment_collection_event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    payment_collection_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("payment_collection_records.payment_collection_id"),
        nullable=False,
    )
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_payment_collection_events_payment_collection_id", "payment_collection_id"),
        Index("ix_payment_collection_events_event_timestamp", "event_timestamp"),
    )
