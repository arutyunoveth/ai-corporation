from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class RFQBatch(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "rfq_batches"

    rfq_batch_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    supplier_shortlist_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_shortlists.supplier_shortlist_id"),
        nullable=False,
    )
    batch_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_rfq_batches_deal_id", "deal_id"),
        Index("ix_rfq_batches_supplier_shortlist_id", "supplier_shortlist_id"),
    )


class RFQRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "rfq_records"

    rfq_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    rfq_batch_id: Mapped[str] = mapped_column(String(64), ForeignKey("rfq_batches.rfq_batch_id"), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(64), ForeignKey("supplier_profiles.supplier_id"), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    rfq_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_rfq_records_batch_id", "rfq_batch_id"),
        Index("ix_rfq_records_supplier_id", "supplier_id"),
    )


class RFQArtifactBinding(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "rfq_artifact_bindings"

    rfq_id: Mapped[str] = mapped_column(String(64), ForeignKey("rfq_records.rfq_id"), nullable=False)
    artifact_ref: Mapped[str] = mapped_column(String(64), ForeignKey("document_artifacts.artifact_ref"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_rfq_artifact_bindings_rfq_id", "rfq_id"),
        Index("ix_rfq_artifact_bindings_artifact_ref", "artifact_ref"),
    )
