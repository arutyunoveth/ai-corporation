from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class QuoteSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quote_sets"

    quote_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    rfq_batch_id: Mapped[str] = mapped_column(String(64), ForeignKey("rfq_batches.rfq_batch_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_quote_sets_deal_id", "deal_id"),
        Index("ix_quote_sets_rfq_batch_id", "rfq_batch_id"),
    )


class QuoteRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quote_records"

    quote_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    quote_set_id: Mapped[str] = mapped_column(String(64), ForeignKey("quote_sets.quote_set_id"), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(64), ForeignKey("supplier_profiles.supplier_id"), nullable=False)
    rfq_id: Mapped[str] = mapped_column(String(64), ForeignKey("rfq_records.rfq_id"), nullable=False)
    supplier_thread_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_communication_threads.supplier_thread_id"),
        nullable=False,
    )
    quote_status: Mapped[str] = mapped_column(Text, nullable=False)
    quoted_amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    quoted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_quote_records_set_id", "quote_set_id"),
        Index("ix_quote_records_supplier_id", "supplier_id"),
        Index("ix_quote_records_rfq_id", "rfq_id"),
    )


class QuoteArtifactBinding(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quote_artifact_bindings"

    quote_id: Mapped[str] = mapped_column(String(64), ForeignKey("quote_records.quote_id"), nullable=False)
    artifact_ref: Mapped[str] = mapped_column(String(64), ForeignKey("document_artifacts.artifact_ref"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_quote_artifact_bindings_quote_id", "quote_id"),
        Index("ix_quote_artifact_bindings_artifact_ref", "artifact_ref"),
    )
