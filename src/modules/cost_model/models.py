from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class CostModelSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "cost_model_sets"

    cost_model_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    quote_comparison_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("quote_comparison_sets.quote_comparison_set_id"),
        nullable=False,
    )
    cost_model_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_cost_model_sets_deal_id", "deal_id"),
        Index("ix_cost_model_sets_quote_comparison_set_id", "quote_comparison_set_id"),
    )


class CostModelRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "cost_model_records"

    cost_model_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    cost_model_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("cost_model_sets.cost_model_set_id"),
        nullable=False,
    )
    base_quote_total: Mapped[float] = mapped_column(Float, nullable=False)
    logistics_cost: Mapped[float] = mapped_column(Float, nullable=False)
    buffer_cost: Mapped[float] = mapped_column(Float, nullable=False)
    overhead_cost: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)
    min_viable_bid: Mapped[float] = mapped_column(Float, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_cost_model_records_set_id", "cost_model_set_id"),
    )


class CostModelLine(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "cost_model_lines"

    cost_model_id: Mapped[str] = mapped_column(String(64), ForeignKey("cost_model_records.cost_model_id"), nullable=False)
    line_code: Mapped[str] = mapped_column(String(64), nullable=False)
    line_type: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_cost_model_lines_cost_model_id", "cost_model_id"),
        Index("ix_cost_model_lines_line_type", "line_type"),
    )
