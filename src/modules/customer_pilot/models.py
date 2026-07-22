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
    current_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tender_analysis_runs.id"), nullable=True
    )
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
        Index("ix_procurement_cases_current_run", "current_run_id"),
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
    artifact_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("pilot_artifacts.id"), nullable=True
    )
    artifact_key: Mapped[str | None] = mapped_column(String(96), nullable=True)
    pdf_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    renderer_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
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


class PilotRunResult(UUIDPrimaryKeyMixin, Base):
    """Server-owned binding between a customer run and its canonical report."""

    __tablename__ = "pilot_run_results"
    customer_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("customer_profiles.customer_id"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pilot_projects.id"), nullable=False
    )
    procurement_case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("procurement_cases.id"), nullable=False
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tender_analysis_runs.id"), nullable=False, unique=True
    )
    source_analysis_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    canonical_report_storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    # ``canonical_report_hash`` is retained as a deprecated R8-pre-096 field.
    # It is never reused as a file hash or frozen report-model identity.
    canonical_report_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_graph_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    production_model_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    requirements_storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements_file_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    canonical_report_file_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    binding_manifest_storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    binding_manifest_file_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_graph_hash_algorithm: Mapped[str | None] = mapped_column(String(64), nullable=True)
    report_model_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verification_policy_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    @property
    def is_verified_snapshot_binding(self) -> bool:
        import re

        hash_value = re.compile(r"^[0-9a-f]{64}$")
        hashes = (
            self.requirements_file_sha256, self.canonical_report_file_sha256,
            self.binding_manifest_file_sha256, self.source_graph_hash,
            self.production_model_hash, self.report_model_hash,
        )
        return bool(
            self.source_analysis_run_id and self.requirements_storage_key
            and self.canonical_report_storage_key and self.binding_manifest_storage_key
            and all(isinstance(value, str) and hash_value.fullmatch(value) for value in hashes)
            and self.source_graph_hash_algorithm == "sha256-json-c14n-v1"
            and self.verification_policy_version == "r8-frozen-canonical-verifier-v1"
        )

    __table_args__ = (
        Index("ix_pilot_run_results_customer_case", "customer_id", "procurement_case_id"),
        Index("ix_pilot_run_results_binding_manifest_key", "binding_manifest_storage_key"),
        Index("ix_pilot_run_results_report_model_hash", "report_model_hash"),
        Index("ix_pilot_run_results_source_graph_hash", "source_graph_hash"),
    )


class PilotArtifact(UUIDPrimaryKeyMixin, Base):
    """Immutable customer-scoped final output. Paths are always data-root relative."""

    __tablename__ = "pilot_artifacts"
    customer_id: Mapped[str] = mapped_column(String(64), ForeignKey("customer_profiles.customer_id"), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("pilot_projects.id"), nullable=False)
    procurement_case_id: Mapped[str] = mapped_column(String(36), ForeignKey("procurement_cases.id"), nullable=False)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("tender_analysis_runs.id"), nullable=False)
    run_result_id: Mapped[str] = mapped_column(String(36), ForeignKey("pilot_run_results.id"), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False, default="final_pdf")
    artifact_key: Mapped[str] = mapped_column(String(96), nullable=False, unique=True)
    report_model_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_graph_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    renderer_version: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="published")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    immutable_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        UniqueConstraint("run_id", "artifact_type", name="uq_pilot_artifact_run_type"),
        Index("ix_pilot_artifacts_customer_case", "customer_id", "procurement_case_id"),
    )
