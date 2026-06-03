from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class SupplierShortlist(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_shortlists"

    supplier_shortlist_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    intake_id: Mapped[str] = mapped_column(String(64), ForeignKey("tender_intake_records.intake_id"), nullable=False)
    document_set_id: Mapped[str] = mapped_column(String(64), ForeignKey("document_sets.document_set_id"), nullable=False)
    tender_summary_id: Mapped[str] = mapped_column(String(64), ForeignKey("tender_summaries.tender_summary_id"), nullable=False)
    shortlist_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_shortlists_deal_id", "deal_id"),
        Index("ix_supplier_shortlists_tender_summary_id", "tender_summary_id"),
    )


class SupplierShortlistRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_shortlist_rows"

    supplier_shortlist_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_shortlists.supplier_shortlist_id"),
        nullable=False,
    )
    supplier_id: Mapped[str] = mapped_column(String(64), ForeignKey("supplier_profiles.supplier_id"), nullable=False)
    rank_order: Mapped[int] = mapped_column(Integer, nullable=False)
    inclusion_reason: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        UniqueConstraint("supplier_shortlist_id", "supplier_id", name="uq_supplier_shortlist_rows_supplier"),
        Index("ix_supplier_shortlist_rows_shortlist_id", "supplier_shortlist_id"),
        Index("ix_supplier_shortlist_rows_supplier_id", "supplier_id"),
    )
