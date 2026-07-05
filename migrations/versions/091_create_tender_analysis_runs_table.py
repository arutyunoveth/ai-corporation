"""create tender analysis runs table

Revision ID: 091_create_tender_analysis_runs_table
Revises: 090_enable_pgvector_and_add_rag_tables
Create Date: 2026-07-05 23:30:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "091_create_tender_analysis_runs_table"
down_revision: str | Sequence[str] | None = "090_enable_pgvector_and_add_rag_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("tender_analysis_runs"):
        op.create_table(
            "tender_analysis_runs",
            sa.Column("id", sa.String(36), primary_key=True, nullable=False),
            sa.Column("registry_number", sa.String(256), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="completed"),
            sa.Column("used_llm", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()),
            sa.Column("llm_model", sa.String(256), nullable=True),
            sa.Column("retrieval_provider", sa.String(64), nullable=True),
            sa.Column("retrieval_model", sa.String(256), nullable=True),
            sa.Column("sections_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("sources_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("report_path", sa.Text(), nullable=True),
            sa.Column("report_markdown_preview", sa.Text(), nullable=True),
            sa.Column("warnings_json", sa.Text(), nullable=True),
            sa.Column("errors_json", sa.Text(), nullable=True),
            sa.Column("duration_seconds", sa.Float(), nullable=True),
            sa.Column("source", sa.String(32), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )

    run_indexes = {item["name"] for item in inspector.get_indexes("tender_analysis_runs")} if inspector.has_table("tender_analysis_runs") else set()
    for idx_name, columns in [
        ("ix_tender_analysis_runs_registry_number", ["registry_number"]),
        ("ix_tender_analysis_runs_status", ["status"]),
        ("ix_tender_analysis_runs_created_at", ["created_at"]),
    ]:
        if idx_name not in run_indexes:
            op.create_index(idx_name, "tender_analysis_runs", columns)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("tender_analysis_runs"):
        op.drop_index("ix_tender_analysis_runs_created_at", table_name="tender_analysis_runs")
        op.drop_index("ix_tender_analysis_runs_status", table_name="tender_analysis_runs")
        op.drop_index("ix_tender_analysis_runs_registry_number", table_name="tender_analysis_runs")
        op.drop_table("tender_analysis_runs")
