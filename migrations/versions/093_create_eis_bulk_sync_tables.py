"""create eis bulk sync tables

Revision ID: 093_create_eis_bulk_sync_tables
Revises: 092_create_tender_analysis_jobs_table
Create Date: 2026-07-10 21:30:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "093_create_eis_bulk_sync_tables"
down_revision: str | Sequence[str] | None = "092_create_tender_analysis_jobs_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("procurement_source_archives"):
        op.create_table(
            "procurement_source_archives",
            sa.Column("id", sa.String(36), primary_key=True, nullable=False),
            sa.Column("source", sa.String(64), nullable=False),
            sa.Column("region_code", sa.String(2), nullable=False),
            sa.Column("source_date", sa.Date(), nullable=False),
            sa.Column("subsystem_type", sa.String(32), nullable=False),
            sa.Column("document_type", sa.String(128), nullable=False),
            sa.Column("archive_url_hash", sa.String(64), nullable=False),
            sa.Column("archive_name", sa.String(1024), nullable=True),
            sa.Column("sha256", sa.String(64), nullable=True),
            sa.Column("size_bytes", sa.Integer(), nullable=True),
            sa.Column("xml_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
            sa.Column("error_summary", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("source", "archive_url_hash", name="uq_procurement_source_archives_source_url_hash"),
            sa.UniqueConstraint("source", "sha256", name="uq_procurement_source_archives_source_sha256"),
        )
        op.create_index("ix_procurement_source_archives_region_date", "procurement_source_archives", ["region_code", "source_date"])
        op.create_index("ix_procurement_source_archives_status", "procurement_source_archives", ["status"])

    if not inspector.has_table("eis_bulk_sync_cursors"):
        op.create_table(
            "eis_bulk_sync_cursors",
            sa.Column("id", sa.String(36), primary_key=True, nullable=False),
            sa.Column("region_code", sa.String(2), nullable=False),
            sa.Column("subsystem_type", sa.String(32), nullable=False),
            sa.Column("document_type", sa.String(128), nullable=False),
            sa.Column("last_requested_date", sa.Date(), nullable=True),
            sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_archive_hash", sa.String(64), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="idle"),
            sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("region_code", "subsystem_type", "document_type", name="uq_eis_bulk_sync_cursors_key"),
        )
        op.create_index("ix_eis_bulk_sync_cursors_next_retry_at", "eis_bulk_sync_cursors", ["next_retry_at"])
        op.create_index("ix_eis_bulk_sync_cursors_status", "eis_bulk_sync_cursors", ["status"])

    if not inspector.has_table("procurement_sync_runs"):
        op.create_table(
            "procurement_sync_runs",
            sa.Column("id", sa.String(36), primary_key=True, nullable=False),
            sa.Column("source", sa.String(64), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="running"),
            sa.Column("mode", sa.String(32), nullable=True),
            sa.Column("region_code", sa.String(2), nullable=True),
            sa.Column("source_date", sa.Date(), nullable=True),
            sa.Column("document_type", sa.String(128), nullable=True),
            sa.Column("stats", sa.JSON(), nullable=True),
            sa.Column("error_summary", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_procurement_sync_runs_source_started_at", "procurement_sync_runs", ["source", "started_at"])
        op.create_index("ix_procurement_sync_runs_status", "procurement_sync_runs", ["status"])

    if not inspector.has_table("procurement_tender_versions"):
        op.create_table(
            "procurement_tender_versions",
            sa.Column("id", sa.String(36), primary_key=True, nullable=False),
            sa.Column("tender_id", sa.String(36), sa.ForeignKey("procurement_tenders.id"), nullable=False),
            sa.Column("source_archive_id", sa.String(36), sa.ForeignKey("procurement_source_archives.id"), nullable=True),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("raw_payload", sa.JSON(), nullable=True),
            sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tender_id", "content_hash", name="uq_procurement_tender_versions_tender_hash"),
        )
        op.create_index("ix_procurement_tender_versions_tender_id", "procurement_tender_versions", ["tender_id"])
        op.create_index("ix_procurement_tender_versions_source_archive_id", "procurement_tender_versions", ["source_archive_id"])
        op.create_index("ix_procurement_tender_versions_content_hash", "procurement_tender_versions", ["content_hash"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("procurement_tender_versions"):
        op.drop_table("procurement_tender_versions")
    if inspector.has_table("procurement_sync_runs"):
        op.drop_table("procurement_sync_runs")
    if inspector.has_table("eis_bulk_sync_cursors"):
        op.drop_table("eis_bulk_sync_cursors")
    if inspector.has_table("procurement_source_archives"):
        op.drop_table("procurement_source_archives")
