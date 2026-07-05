"""create tender analysis jobs table

Revision ID: 092_create_tender_analysis_jobs_table
Revises: 091_create_tender_analysis_runs_table
Create Date: 2026-07-06 01:30:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "092_create_tender_analysis_jobs_table"
down_revision: str | Sequence[str] | None = "091_create_tender_analysis_runs_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("tender_analysis_jobs"):
        op.create_table(
            "tender_analysis_jobs",
            sa.Column("id", sa.String(36), primary_key=True, nullable=False),
            sa.Column("job_type", sa.String(32), nullable=False),
            sa.Column("registry_number", sa.String(256), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
            sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("current_step", sa.String(64), nullable=True),
            sa.Column("steps_json", sa.Text(), nullable=True),
            sa.Column("result_json", sa.Text(), nullable=True),
            sa.Column("warnings_json", sa.Text(), nullable=True),
            sa.Column("errors_json", sa.Text(), nullable=True),
            sa.Column("report_path", sa.Text(), nullable=True),
            sa.Column("analysis_run_id", sa.String(36), nullable=True),
            sa.Column("request_json", sa.Text(), nullable=True),
            sa.Column("source", sa.String(32), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("duration_seconds", sa.Float(), nullable=True),
        )

    indexes = (
        {item["name"] for item in inspector.get_indexes("tender_analysis_jobs")}
        if inspector.has_table("tender_analysis_jobs")
        else set()
    )
    for idx_name, columns in [
        ("ix_tender_analysis_jobs_registry_number", ["registry_number"]),
        ("ix_tender_analysis_jobs_job_type", ["job_type"]),
        ("ix_tender_analysis_jobs_status", ["status"]),
        ("ix_tender_analysis_jobs_created_at", ["created_at"]),
    ]:
        if idx_name not in indexes:
            op.create_index(idx_name, "tender_analysis_jobs", columns)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("tender_analysis_jobs"):
        op.drop_index("ix_tender_analysis_jobs_created_at", table_name="tender_analysis_jobs")
        op.drop_index("ix_tender_analysis_jobs_status", table_name="tender_analysis_jobs")
        op.drop_index("ix_tender_analysis_jobs_job_type", table_name="tender_analysis_jobs")
        op.drop_index("ix_tender_analysis_jobs_registry_number", table_name="tender_analysis_jobs")
        op.drop_table("tender_analysis_jobs")
