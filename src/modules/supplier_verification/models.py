from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class SupplierVerificationSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_verification_sets"

    supplier_verification_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    supplier_shortlist_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_shortlists.supplier_shortlist_id"),
        nullable=False,
    )
    verification_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_verification_sets_deal_id", "deal_id"),
        Index("ix_supplier_verification_sets_shortlist_id", "supplier_shortlist_id"),
    )


class SupplierVerificationRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_verification_records"

    supplier_verification_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    supplier_verification_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_verification_sets.supplier_verification_set_id"),
        nullable=False,
    )
    supplier_id: Mapped[str] = mapped_column(String(64), ForeignKey("supplier_profiles.supplier_id"), nullable=False)
    verification_result: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_verification_records_set_id", "supplier_verification_set_id"),
        Index("ix_supplier_verification_records_supplier_id", "supplier_id"),
    )


class SupplierVerificationFlag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_verification_flags"

    supplier_verification_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_verification_records.supplier_verification_id"),
        nullable=False,
    )
    flag_code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_verification_flags_verification_id", "supplier_verification_id"),
        Index("ix_supplier_verification_flags_severity", "severity"),
    )
