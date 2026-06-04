"""create knowledge asset tables

Revision ID: 082_create_knowledge_assets
Revises: 081_create_supplier_ratings
Create Date: 2026-06-04 15:30:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "082_create_knowledge_assets"
down_revision: str | Sequence[str] | None = "081_create_supplier_ratings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_asset_sets",
        sa.Column("knowledge_asset_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), nullable=False),
        sa.Column("postmortem_set_id", sa.String(length=64), nullable=False),
        sa.Column("archive_export_set_id", sa.String(length=64), nullable=True),
        sa.Column("dashboard_snapshot_set_id", sa.String(length=64), nullable=True),
        sa.Column("knowledge_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["archive_export_set_id"], ["archive_export_sets.archive_export_set_id"]),
        sa.ForeignKeyConstraint(["dashboard_snapshot_set_id"], ["dashboard_snapshot_sets.dashboard_snapshot_set_id"]),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.deal_id"]),
        sa.ForeignKeyConstraint(["postmortem_set_id"], ["postmortem_sets.postmortem_set_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("knowledge_asset_set_id"),
    )
    op.create_index("ix_knowledge_asset_sets_deal_id", "knowledge_asset_sets", ["deal_id"])
    op.create_index("ix_knowledge_asset_sets_postmortem_set_id", "knowledge_asset_sets", ["postmortem_set_id"])

    op.create_table(
        "knowledge_asset_records",
        sa.Column("knowledge_asset_id", sa.String(length=64), nullable=False),
        sa.Column("knowledge_asset_set_id", sa.String(length=64), nullable=False),
        sa.Column("asset_title", sa.Text(), nullable=False),
        sa.Column("asset_type", sa.Text(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("asset_payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_asset_set_id"], ["knowledge_asset_sets.knowledge_asset_set_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("knowledge_asset_id"),
    )
    op.create_index("ix_knowledge_asset_records_set_id", "knowledge_asset_records", ["knowledge_asset_set_id"])

    op.create_table(
        "knowledge_asset_links",
        sa.Column("knowledge_asset_id", sa.String(length=64), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_asset_id"], ["knowledge_asset_records.knowledge_asset_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_asset_links_knowledge_asset_id", "knowledge_asset_links", ["knowledge_asset_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_asset_links_knowledge_asset_id", table_name="knowledge_asset_links")
    op.drop_table("knowledge_asset_links")
    op.drop_index("ix_knowledge_asset_records_set_id", table_name="knowledge_asset_records")
    op.drop_table("knowledge_asset_records")
    op.drop_index("ix_knowledge_asset_sets_postmortem_set_id", table_name="knowledge_asset_sets")
    op.drop_index("ix_knowledge_asset_sets_deal_id", table_name="knowledge_asset_sets")
    op.drop_table("knowledge_asset_sets")
