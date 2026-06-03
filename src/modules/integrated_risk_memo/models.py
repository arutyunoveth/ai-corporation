from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class IntegratedRiskMemoSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "integrated_risk_memo_sets"

    integrated_risk_memo_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    initial_tech_risk_flag_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("initial_tech_risk_flag_sets.risk_flag_set_id"),
        nullable=False,
    )
    supplier_verification_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_verification_sets.supplier_verification_set_id"),
        nullable=False,
    )
    quote_comparison_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("quote_comparison_sets.quote_comparison_set_id"),
        nullable=False,
    )
    finance_memo_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("finance_memo_sets.finance_memo_set_id"),
        nullable=False,
    )
    contract_risk_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("contract_risk_sets.contract_risk_set_id"),
        nullable=False,
    )
    memo_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_integrated_risk_memo_sets_deal_id", "deal_id"),
        Index("ix_integrated_risk_memo_sets_finance_memo_set_id", "finance_memo_set_id"),
    )


class IntegratedRiskMemoRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "integrated_risk_memo_records"

    integrated_risk_memo_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    integrated_risk_memo_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("integrated_risk_memo_sets.integrated_risk_memo_set_id"),
        nullable=False,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_summary_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_integrated_risk_memo_records_set_id", "integrated_risk_memo_set_id"),
    )


class IntegratedRiskItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "integrated_risk_items"

    integrated_risk_memo_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("integrated_risk_memo_records.integrated_risk_memo_id"),
        nullable=False,
    )
    risk_source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_object_ref: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    mitigation_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_integrated_risk_items_integrated_risk_memo_id", "integrated_risk_memo_id"),
        Index("ix_integrated_risk_items_source_type", "risk_source_type"),
        Index("ix_integrated_risk_items_severity", "severity"),
    )
