from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class ComplianceMatrix(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "compliance_matrices"

    compliance_matrix_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    intake_id: Mapped[str] = mapped_column(String(64), ForeignKey("tender_intake_records.intake_id"), nullable=False)
    document_set_id: Mapped[str] = mapped_column(String(64), ForeignKey("document_sets.document_set_id"), nullable=False)
    tender_summary_id: Mapped[str] = mapped_column(String(64), ForeignKey("tender_summaries.tender_summary_id"), nullable=False)
    matrix_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ambiguous_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_risk_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requires_manual_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_compliance_matrices_deal_id", "deal_id"),
        Index("ix_compliance_matrices_document_set_id", "document_set_id"),
    )


class ComplianceMatrixRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "compliance_matrix_rows"

    compliance_matrix_id: Mapped[str] = mapped_column(String(64), ForeignKey("compliance_matrices.compliance_matrix_id"), nullable=False)
    row_code: Mapped[str] = mapped_column(String(32), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_category: Mapped[str] = mapped_column(Text, nullable=False)
    compliance_status: Mapped[str] = mapped_column(Text, nullable=False)
    source_artifact_ref: Mapped[str | None] = mapped_column(String(64), ForeignKey("document_artifacts.artifact_ref"), nullable=True)
    source_pointer: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requires_manual_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        UniqueConstraint("compliance_matrix_id", "row_code", name="uq_compliance_matrix_rows_code"),
        Index("ix_compliance_matrix_rows_matrix_id", "compliance_matrix_id"),
        Index("ix_compliance_matrix_rows_status", "compliance_status"),
        Index("ix_compliance_matrix_rows_source_artifact_ref", "source_artifact_ref"),
    )

