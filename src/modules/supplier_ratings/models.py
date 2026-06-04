from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class SupplierRatingUpdateSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_rating_update_sets"

    supplier_rating_update_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(64), ForeignKey("supplier_profiles.supplier_id"), nullable=False)
    supplier_contract_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_contract_sets.supplier_contract_set_id"),
        nullable=False,
    )
    postmortem_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("postmortem_sets.postmortem_set_id"),
        nullable=False,
    )
    rating_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_rating_update_sets_deal_id", "deal_id"),
        Index("ix_supplier_rating_update_sets_supplier_id", "supplier_id"),
    )


class SupplierRatingUpdateRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_rating_update_records"

    supplier_rating_update_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    supplier_rating_update_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_rating_update_sets.supplier_rating_update_set_id"),
        nullable=False,
    )
    prior_rating_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_rating_value: Mapped[float] = mapped_column(Float, nullable=False)
    rating_band: Mapped[str] = mapped_column(Text, nullable=False)
    rationale_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_rating_update_records_set_id", "supplier_rating_update_set_id"),
    )


class SupplierRatingFactor(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_rating_factors"

    supplier_rating_update_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_rating_update_records.supplier_rating_update_id"),
        nullable=False,
    )
    factor_code: Mapped[str] = mapped_column(String(64), nullable=False)
    factor_score: Mapped[float] = mapped_column(Float, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_rating_factors_update_id", "supplier_rating_update_id"),
        Index("ix_supplier_rating_factors_factor_code", "factor_code"),
    )
