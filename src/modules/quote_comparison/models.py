from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class QuoteComparisonSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quote_comparison_sets"

    quote_comparison_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    quote_set_id: Mapped[str] = mapped_column(String(64), ForeignKey("quote_sets.quote_set_id"), nullable=False)
    supplier_verification_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_verification_sets.supplier_verification_set_id"),
        nullable=False,
    )
    comparison_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_quote_comparison_sets_deal_id", "deal_id"),
        Index("ix_quote_comparison_sets_quote_set_id", "quote_set_id"),
    )


class QuoteComparisonRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quote_comparison_rows"

    quote_comparison_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("quote_comparison_sets.quote_comparison_set_id"),
        nullable=False,
    )
    quote_id: Mapped[str] = mapped_column(String(64), ForeignKey("quote_records.quote_id"), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(64), ForeignKey("supplier_profiles.supplier_id"), nullable=False)
    price_score: Mapped[float] = mapped_column(Float, nullable=False)
    delivery_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    rank_order: Mapped[int] = mapped_column(Integer, nullable=False)
    comparison_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_quote_comparison_rows_set_id", "quote_comparison_set_id"),
        Index("ix_quote_comparison_rows_quote_id", "quote_id"),
        Index("ix_quote_comparison_rows_supplier_id", "supplier_id"),
    )


class QuoteComparisonRecommendation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quote_comparison_recommendations"

    quote_comparison_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("quote_comparison_sets.quote_comparison_set_id"),
        nullable=False,
    )
    recommended_quote_id: Mapped[str] = mapped_column(String(64), ForeignKey("quote_records.quote_id"), nullable=False)
    recommended_supplier_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_profiles.supplier_id"),
        nullable=False,
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_quote_comparison_recommendations_set_id", "quote_comparison_set_id"),
    )
