from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import UUIDPrimaryKeyMixin, Base, utcnow


class AgentMemory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "hermes_agent_memory"

    memory_type: Mapped[str] = mapped_column(String(64), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    category: Mapped[str] = mapped_column(String(128), nullable=False, default="general")
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source_tender_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("procurement_tenders.id"), nullable=True)
    source_analysis_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_hermes_agent_memory_memory_type", "memory_type"),
        Index("ix_hermes_agent_memory_scope", "scope"),
        Index("ix_hermes_agent_memory_source_tender_id", "source_tender_id"),
    )


class TenderAnalysisFeedback(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "hermes_tender_analysis_feedback"

    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("procurement_tenders.id"), nullable=False, index=True)
    analysis_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    field_path: Mapped[str] = mapped_column(String(256), nullable=False)
    feedback_type: Mapped[str] = mapped_column(String(32), nullable=False)
    user_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_value_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_hermes_feedback_tender_id", "tender_id"),
        Index("ix_hermes_feedback_analysis_id", "analysis_id"),
    )


class TenderEvalCase(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "hermes_tender_eval_cases"

    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("procurement_tenders.id"), nullable=False, index=True)
    fixture_name: Mapped[str] = mapped_column(String(256), nullable=False)
    expected_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    must_include_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    must_not_include_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_hermes_eval_cases_tender_id", "tender_id"),
        Index("ix_hermes_eval_cases_fixture_name", "fixture_name"),
    )


class DocumentEvidenceSpan(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "hermes_document_evidence_spans"

    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("procurement_tenders.id"), nullable=False, index=True)
    document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("procurement_tender_documents.id"), nullable=True)
    document_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    field_path: Mapped[str] = mapped_column(String(256), nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_hermes_evidence_tender_id", "tender_id"),
        Index("ix_hermes_evidence_document_id", "document_id"),
        Index("ix_hermes_evidence_field_path", "field_path"),
    )


class AnalysisQualityCheck(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "hermes_analysis_quality_checks"

    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("procurement_tenders.id"), nullable=False, index=True)
    analysis_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    check_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_hermes_quality_checks_tender_id", "tender_id"),
        Index("ix_hermes_quality_checks_analysis_id", "analysis_id"),
        Index("ix_hermes_quality_checks_check_name", "check_name"),
    )
