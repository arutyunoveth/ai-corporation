from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class FinancingStrategySet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "financing_strategy_sets"

    financing_strategy_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    cash_gap_set_id: Mapped[str] = mapped_column(String(64), ForeignKey("cash_gap_sets.cash_gap_set_id"), nullable=False)
    strategy_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_financing_strategy_sets_deal_id", "deal_id"),
        Index("ix_financing_strategy_sets_cash_gap_set_id", "cash_gap_set_id"),
    )


class FinancingStrategyRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "financing_strategy_records"

    financing_strategy_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    financing_strategy_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("financing_strategy_sets.financing_strategy_set_id"),
        nullable=False,
    )
    recommended_option_code: Mapped[str] = mapped_column(String(64), nullable=False)
    feasible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_financing_strategy_records_set_id", "financing_strategy_set_id"),
    )


class FinancingStrategyOption(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "financing_strategy_options"

    financing_strategy_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("financing_strategy_records.financing_strategy_id"),
        nullable=False,
    )
    option_code: Mapped[str] = mapped_column(String(64), nullable=False)
    option_name: Mapped[str] = mapped_column(Text, nullable=False)
    funding_amount: Mapped[float] = mapped_column(Float, nullable=False)
    funding_cost: Mapped[float] = mapped_column(Float, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    feasibility_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_financing_strategy_options_financing_strategy_id", "financing_strategy_id"),
        Index("ix_financing_strategy_options_option_code", "option_code"),
    )
