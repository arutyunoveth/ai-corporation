from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class CashGapSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "cash_gap_sets"

    cash_gap_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    cost_model_set_id: Mapped[str] = mapped_column(String(64), ForeignKey("cost_model_sets.cost_model_set_id"), nullable=False)
    cash_gap_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_cash_gap_sets_deal_id", "deal_id"),
        Index("ix_cash_gap_sets_cost_model_set_id", "cost_model_set_id"),
    )


class CashGapRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "cash_gap_records"

    cash_gap_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    cash_gap_set_id: Mapped[str] = mapped_column(String(64), ForeignKey("cash_gap_sets.cash_gap_set_id"), nullable=False)
    peak_gap_amount: Mapped[float] = mapped_column(Float, nullable=False)
    gap_duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_cash_gap_records_set_id", "cash_gap_set_id"),
    )


class CashGapScenario(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "cash_gap_scenarios"

    cash_gap_id: Mapped[str] = mapped_column(String(64), ForeignKey("cash_gap_records.cash_gap_id"), nullable=False)
    scenario_code: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_name: Mapped[str] = mapped_column(Text, nullable=False)
    peak_gap_amount: Mapped[float] = mapped_column(Float, nullable=False)
    gap_duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_cash_gap_scenarios_cash_gap_id", "cash_gap_id"),
        Index("ix_cash_gap_scenarios_scenario_code", "scenario_code"),
    )
