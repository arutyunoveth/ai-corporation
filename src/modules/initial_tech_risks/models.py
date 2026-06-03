from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class InitialTechRiskFlagSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "initial_tech_risk_flag_sets"

    risk_flag_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    intake_id: Mapped[str] = mapped_column(String(64), ForeignKey("tender_intake_records.intake_id"), nullable=False)
    document_set_id: Mapped[str] = mapped_column(String(64), ForeignKey("document_sets.document_set_id"), nullable=False)
    tender_summary_id: Mapped[str] = mapped_column(String(64), ForeignKey("tender_summaries.tender_summary_id"), nullable=False)
    compliance_matrix_id: Mapped[str] = mapped_column(String(64), ForeignKey("compliance_matrices.compliance_matrix_id"), nullable=False)
    document_requirement_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("document_requirement_sets.document_requirement_set_id"),
        nullable=False,
    )
    risk_flag_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overall_risk_severity: Mapped[str] = mapped_column(Text, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_initial_tech_risk_flag_sets_deal_id", "deal_id"),
        Index("ix_initial_tech_risk_flag_sets_matrix_id", "compliance_matrix_id"),
    )


class InitialTechRiskFlag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "initial_tech_risk_flags"

    risk_flag_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("initial_tech_risk_flag_sets.risk_flag_set_id"),
        nullable=False,
    )
    row_code: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_code: Mapped[str] = mapped_column(Text, nullable=False)
    risk_category: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    mitigation_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    requires_manual_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("risk_flag_set_id", "row_code", name="uq_initial_tech_risk_flags_code"),
        Index("ix_initial_tech_risk_flags_set_id", "risk_flag_set_id"),
        Index("ix_initial_tech_risk_flags_category", "risk_category"),
        Index("ix_initial_tech_risk_flags_severity", "severity"),
    )
