from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class CEOApprovalSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ceo_approval_sets"

    ceo_approval_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    finance_memo_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("finance_memo_sets.finance_memo_set_id"),
        nullable=False,
    )
    integrated_risk_memo_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("integrated_risk_memo_sets.integrated_risk_memo_set_id"),
        nullable=False,
    )
    approval_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_ceo_approval_sets_deal_id", "deal_id"),
        Index("ix_ceo_approval_sets_finance_memo_set_id", "finance_memo_set_id"),
    )


class CEOApprovalRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ceo_approval_records"

    ceo_approval_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    ceo_approval_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("ceo_approval_sets.ceo_approval_set_id"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    decided_by_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_ceo_approval_records_set_id", "ceo_approval_set_id"),
        Index("ix_ceo_approval_records_decision", "decision"),
    )


class CEOApprovalCondition(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ceo_approval_conditions"

    ceo_approval_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("ceo_approval_records.ceo_approval_id"),
        nullable=False,
    )
    condition_code: Mapped[str] = mapped_column(String(64), nullable=False)
    condition_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_ceo_approval_conditions_ceo_approval_id", "ceo_approval_id"),
        Index("ix_ceo_approval_conditions_condition_code", "condition_code"),
    )
