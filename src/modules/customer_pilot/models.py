from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class PilotProject(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "pilot_projects"
    customer_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("customer_profiles.customer_id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    internal_slug: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    __table_args__ = (
        UniqueConstraint("customer_id", "internal_slug"),
        Index("ix_pilot_projects_customer", "customer_id"),
    )


class ProcurementCase(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "procurement_cases"
    customer_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("customer_profiles.customer_id"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pilot_projects.id"), nullable=False
    )
    procurement_number: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created")
    artifact_key: Mapped[str] = mapped_column(String(96), nullable=False, unique=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    __table_args__ = (
        UniqueConstraint("customer_id", "project_id", "procurement_number"),
        Index("ix_procurement_cases_customer_project", "customer_id", "project_id"),
        Index("ix_procurement_cases_status", "status"),
    )


class PilotReview(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "pilot_reviews"
    customer_id: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    procurement_case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("procurement_cases.id"), nullable=False
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tender_analysis_runs.id"), nullable=False, unique=True
    )
    reviewer: Mapped[str] = mapped_column(String(256), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    checklist: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    internal_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_graph_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    report_model_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    artifact_hashes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    immutable_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    __table_args__ = (
        Index("ix_pilot_reviews_customer_case", "customer_id", "procurement_case_id"),
    )


class PilotFeedback(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "pilot_feedback"
    customer_id: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    procurement_case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("procurement_cases.id"), nullable=False
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tender_analysis_runs.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    expected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    __table_args__ = (
        Index("ix_pilot_feedback_customer_case", "customer_id", "procurement_case_id"),
    )


class PilotAuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "pilot_audit_events"
    customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    procurement_case_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    __table_args__ = (
        Index("ix_pilot_audit_customer_created", "customer_id", "created_at"),
    )
