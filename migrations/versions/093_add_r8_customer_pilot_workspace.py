"""add R8 customer pilot workspace

Revision ID: 093_add_r8_customer_pilot_workspace
Revises: 092_create_tender_analysis_jobs_table
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "093_add_r8_customer_pilot_workspace"
down_revision: str | Sequence[str] | None = "092_create_tender_analysis_jobs_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("pilot_projects"):
        op.create_table(
            "pilot_projects",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "customer_id",
                sa.String(64),
                sa.ForeignKey("customer_profiles.customer_id"),
                nullable=False,
            ),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("internal_slug", sa.String(80), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("customer_id", "internal_slug"),
        )
        op.create_index("ix_pilot_projects_customer", "pilot_projects", ["customer_id"])
    if not inspector.has_table("procurement_cases"):
        op.create_table(
            "procurement_cases",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "customer_id",
                sa.String(64),
                sa.ForeignKey("customer_profiles.customer_id"),
                nullable=False,
            ),
            sa.Column(
                "project_id",
                sa.String(36),
                sa.ForeignKey("pilot_projects.id"),
                nullable=False,
            ),
            sa.Column("procurement_number", sa.String(256)),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("artifact_key", sa.String(96), nullable=False, unique=True),
            sa.Column("error_message", sa.Text()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("customer_id", "project_id", "procurement_number"),
        )
        op.create_index(
            "ix_procurement_cases_customer_project",
            "procurement_cases",
            ["customer_id", "project_id"],
        )
        op.create_index("ix_procurement_cases_status", "procurement_cases", ["status"])
    for name in ("pilot_reviews", "pilot_feedback", "pilot_audit_events"):
        if inspector.has_table(name):
            continue
        if name == "pilot_reviews":
            op.create_table(
                name,
                sa.Column("id", sa.String(36), primary_key=True),
                sa.Column("customer_id", sa.String(64), nullable=False),
                sa.Column("project_id", sa.String(36), nullable=False),
                sa.Column(
                    "procurement_case_id",
                    sa.String(36),
                    sa.ForeignKey("procurement_cases.id"),
                    nullable=False,
                ),
                sa.Column(
                    "run_id",
                    sa.String(36),
                    sa.ForeignKey("tender_analysis_runs.id"),
                    nullable=False,
                    unique=True,
                ),
                sa.Column("reviewer", sa.String(256), nullable=False),
                sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
                sa.Column("verdict", sa.String(32), nullable=False),
                sa.Column("checklist", sa.JSON(), nullable=False),
                sa.Column("internal_comment", sa.Text()),
                sa.Column("client_comment", sa.Text()),
                sa.Column("source_graph_hash", sa.String(64)),
                sa.Column("report_model_hash", sa.String(64)),
                sa.Column("artifact_hashes", sa.JSON(), nullable=False),
                sa.Column("immutable_at", sa.DateTime(timezone=True)),
            )
            op.create_index(
                "ix_pilot_reviews_customer_case",
                name,
                ["customer_id", "procurement_case_id"],
            )
        elif name == "pilot_feedback":
            op.create_table(
                name,
                sa.Column("id", sa.String(36), primary_key=True),
                sa.Column("customer_id", sa.String(64), nullable=False),
                sa.Column("project_id", sa.String(36), nullable=False),
                sa.Column(
                    "procurement_case_id",
                    sa.String(36),
                    sa.ForeignKey("procurement_cases.id"),
                    nullable=False,
                ),
                sa.Column(
                    "run_id",
                    sa.String(36),
                    sa.ForeignKey("tender_analysis_runs.id"),
                    nullable=False,
                ),
                sa.Column("category", sa.String(64), nullable=False),
                sa.Column("severity", sa.String(32), nullable=False),
                sa.Column("expected_value", sa.Text()),
                sa.Column("observed_value", sa.Text()),
                sa.Column("comment", sa.Text()),
                sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
                sa.Column("resolved_at", sa.DateTime(timezone=True)),
            )
            op.create_index(
                "ix_pilot_feedback_customer_case",
                name,
                ["customer_id", "procurement_case_id"],
            )
        else:
            op.create_table(
                name,
                sa.Column("id", sa.String(36), primary_key=True),
                sa.Column("customer_id", sa.String(64)),
                sa.Column("project_id", sa.String(36)),
                sa.Column("procurement_case_id", sa.String(36)),
                sa.Column("run_id", sa.String(36)),
                sa.Column("event_type", sa.String(64), nullable=False),
                sa.Column("payload", sa.JSON(), nullable=False),
                sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            )
            op.create_index(
                "ix_pilot_audit_customer_created", name, ["customer_id", "created_at"]
            )
    columns = {x["name"] for x in inspector.get_columns("tender_analysis_runs")}
    # SQLite cannot ALTER in a foreign-key constraint. The workflow validates these
    # links atomically and fresh PostgreSQL deployments receive the model FKs.
    for name, type_ in [
        ("customer_id", sa.String(64)),
        ("project_id", sa.String(36)),
        ("procurement_case_id", sa.String(36)),
        ("idempotency_key", sa.String(128)),
        ("artifact_key", sa.String(96)),
    ]:
        if name not in columns:
            op.add_column("tender_analysis_runs", sa.Column(name, type_, nullable=True))
    # PostgreSQL receives explicit database-enforced references. SQLite supports
    # the same migration path but cannot ALTER TABLE to add a foreign key.
    if bind.dialect.name == "postgresql":
        foreign_keys = {
            item["name"] for item in inspector.get_foreign_keys("tender_analysis_runs")
        }
        for name, column, target in [
            ("fk_r8_runs_customer", "customer_id", "customer_profiles.customer_id"),
            ("fk_r8_runs_project", "project_id", "pilot_projects.id"),
            ("fk_r8_runs_case", "procurement_case_id", "procurement_cases.id"),
        ]:
            if name not in foreign_keys:
                op.create_foreign_key(
                    name,
                    "tender_analysis_runs",
                    target.split(".")[0],
                    [column],
                    [target.split(".")[1]],
                )
    indexes = {x["name"] for x in inspector.get_indexes("tender_analysis_runs")}
    if "ix_tender_analysis_runs_customer_project_case" not in indexes:
        op.create_index(
            "ix_tender_analysis_runs_customer_project_case",
            "tender_analysis_runs",
            ["customer_id", "project_id", "procurement_case_id"],
        )
    if "ux_r8_run_case_idempotency" not in indexes:
        op.create_index(
            "ux_r8_run_case_idempotency",
            "tender_analysis_runs",
            ["procurement_case_id", "idempotency_key"],
            unique=True,
        )
    if "ux_tender_analysis_runs_artifact_key" not in indexes:
        op.create_index(
            "ux_tender_analysis_runs_artifact_key",
            "tender_analysis_runs",
            ["artifact_key"],
            unique=True,
        )


def downgrade() -> None:
    # R8 data is intentionally retained: rollout uses forward-only pilot migrations.
    pass
