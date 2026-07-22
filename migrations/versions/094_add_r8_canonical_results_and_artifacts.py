"""add R8 canonical result bindings and immutable pilot artifacts

Revision ID: 094_add_r8_canonical_results_and_artifacts
Revises: 093_add_r8_customer_pilot_workspace
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "094_add_r8_canonical_results_and_artifacts"
down_revision: str | Sequence[str] | None = "093_add_r8_customer_pilot_workspace"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("pilot_run_results"):
        op.create_table(
            "pilot_run_results",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("customer_id", sa.String(64), sa.ForeignKey("customer_profiles.customer_id"), nullable=False),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("pilot_projects.id"), nullable=False),
            sa.Column("procurement_case_id", sa.String(36), sa.ForeignKey("procurement_cases.id"), nullable=False),
            sa.Column("run_id", sa.String(36), sa.ForeignKey("tender_analysis_runs.id"), nullable=False, unique=True),
            sa.Column("source_analysis_run_id", sa.String(36)),
            sa.Column("canonical_report_storage_key", sa.Text(), nullable=False),
            sa.Column("canonical_report_hash", sa.String(64), nullable=False),
            sa.Column("source_graph_hash", sa.String(64), nullable=False),
            sa.Column("production_model_hash", sa.String(64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_pilot_run_results_customer_case", "pilot_run_results", ["customer_id", "procurement_case_id"])
    if not inspector.has_table("pilot_artifacts"):
        op.create_table(
            "pilot_artifacts",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("customer_id", sa.String(64), sa.ForeignKey("customer_profiles.customer_id"), nullable=False),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("pilot_projects.id"), nullable=False),
            sa.Column("procurement_case_id", sa.String(36), sa.ForeignKey("procurement_cases.id"), nullable=False),
            sa.Column("run_id", sa.String(36), sa.ForeignKey("tender_analysis_runs.id"), nullable=False),
            sa.Column("run_result_id", sa.String(36), sa.ForeignKey("pilot_run_results.id"), nullable=False),
            sa.Column("artifact_type", sa.String(32), nullable=False),
            sa.Column("artifact_key", sa.String(96), nullable=False, unique=True),
            sa.Column("report_model_hash", sa.String(64), nullable=False),
            sa.Column("source_graph_hash", sa.String(64), nullable=False),
            sa.Column("renderer_version", sa.String(64), nullable=False),
            sa.Column("manifest_relative_path", sa.Text(), nullable=False),
            sa.Column("pdf_relative_path", sa.Text(), nullable=False),
            sa.Column("pdf_sha256", sa.String(64), nullable=False),
            sa.Column("byte_size", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("immutable_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("run_id", "artifact_type", name="uq_pilot_artifact_run_type"),
        )
        op.create_index("ix_pilot_artifacts_customer_case", "pilot_artifacts", ["customer_id", "procurement_case_id"])
    columns = {item["name"] for item in inspector.get_columns("pilot_reviews")}
    for name, type_ in [("artifact_id", sa.String(36)), ("artifact_key", sa.String(96)), ("pdf_sha256", sa.String(64)), ("renderer_version", sa.String(64))]:
        if name not in columns:
            op.add_column("pilot_reviews", sa.Column(name, type_, nullable=True))
    if bind.dialect.name == "postgresql":
        foreign_keys = {item["name"] for item in inspector.get_foreign_keys("pilot_reviews")}
        if "fk_pilot_reviews_artifact" not in foreign_keys:
            op.create_foreign_key("fk_pilot_reviews_artifact", "pilot_reviews", "pilot_artifacts", ["artifact_id"], ["id"])


def downgrade() -> None:
    # Forward-only pilot migration: never destroy customer artifacts during rollback.
    pass
