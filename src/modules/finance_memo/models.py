from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class FinanceMemoSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "finance_memo_sets"

    finance_memo_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    cost_model_set_id: Mapped[str] = mapped_column(String(64), ForeignKey("cost_model_sets.cost_model_set_id"), nullable=False)
    cash_gap_set_id: Mapped[str] = mapped_column(String(64), ForeignKey("cash_gap_sets.cash_gap_set_id"), nullable=False)
    financing_strategy_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("financing_strategy_sets.financing_strategy_set_id"),
        nullable=False,
    )
    memo_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_finance_memo_sets_deal_id", "deal_id"),
        Index("ix_finance_memo_sets_cost_model_set_id", "cost_model_set_id"),
    )


class FinanceMemoRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "finance_memo_records"

    finance_memo_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    finance_memo_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("finance_memo_sets.finance_memo_set_id"),
        nullable=False,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_summary_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_finance_memo_records_set_id", "finance_memo_set_id"),
    )


class FinanceMemoFlag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "finance_memo_flags"

    finance_memo_id: Mapped[str] = mapped_column(String(64), ForeignKey("finance_memo_records.finance_memo_id"), nullable=False)
    flag_code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_finance_memo_flags_finance_memo_id", "finance_memo_id"),
        Index("ix_finance_memo_flags_severity", "severity"),
    )
