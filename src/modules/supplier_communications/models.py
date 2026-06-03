from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class SupplierCommunicationSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_communication_sets"

    supplier_communication_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    rfq_batch_id: Mapped[str] = mapped_column(String(64), ForeignKey("rfq_batches.rfq_batch_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_communication_sets_deal_id", "deal_id"),
        Index("ix_supplier_communication_sets_rfq_batch_id", "rfq_batch_id"),
    )


class SupplierCommunicationThread(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_communication_threads"

    supplier_thread_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    supplier_communication_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_communication_sets.supplier_communication_set_id"),
        nullable=False,
    )
    supplier_id: Mapped[str] = mapped_column(String(64), ForeignKey("supplier_profiles.supplier_id"), nullable=False)
    rfq_id: Mapped[str] = mapped_column(String(64), ForeignKey("rfq_records.rfq_id"), nullable=False)
    thread_status: Mapped[str] = mapped_column(Text, nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_communication_threads_set_id", "supplier_communication_set_id"),
        Index("ix_supplier_communication_threads_supplier_id", "supplier_id"),
        Index("ix_supplier_communication_threads_rfq_id", "rfq_id"),
    )


class SupplierMessageRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_message_records"

    supplier_message_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    supplier_thread_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_communication_threads.supplier_thread_id"),
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(String(32), nullable=False)
    message_subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    linked_artifact_ref: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("document_artifacts.artifact_ref"),
        nullable=True,
    )
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_message_records_thread_id", "supplier_thread_id"),
        Index("ix_supplier_message_records_direction", "direction"),
    )
