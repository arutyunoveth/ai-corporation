"""create archive export tables"""

from alembic import op
import sqlalchemy as sa

revision = "046_create_archive_export"
down_revision = "045_create_dashboard_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "archive_export_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("archive_export_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "deal_closure_set_id",
            sa.String(length=64),
            sa.ForeignKey("deal_closure_sets.deal_closure_set_id"),
            nullable=False,
        ),
        sa.Column("export_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("archive_export_set_id"),
    )
    op.create_index("ix_archive_export_sets_deal_id", "archive_export_sets", ["deal_id"])
    op.create_index("ix_archive_export_sets_deal_closure_set_id", "archive_export_sets", ["deal_closure_set_id"])

    op.create_table(
        "archive_export_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("archive_export_id", sa.String(length=64), nullable=False),
        sa.Column(
            "archive_export_set_id",
            sa.String(length=64),
            sa.ForeignKey("archive_export_sets.archive_export_set_id"),
            nullable=False,
        ),
        sa.Column("export_manifest_json", sa.JSON(), nullable=False),
        sa.Column("export_format", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("archive_export_id"),
    )
    op.create_index("ix_archive_export_records_set_id", "archive_export_records", ["archive_export_set_id"])

    op.create_table(
        "archive_export_items",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "archive_export_id",
            sa.String(length=64),
            sa.ForeignKey("archive_export_records.archive_export_id"),
            nullable=False,
        ),
        sa.Column("artifact_ref", sa.String(length=64), sa.ForeignKey("document_artifacts.artifact_ref"), nullable=False),
        sa.Column("item_role", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_archive_export_items_archive_export_id", "archive_export_items", ["archive_export_id"])
    op.create_index("ix_archive_export_items_artifact_ref", "archive_export_items", ["artifact_ref"])


def downgrade() -> None:
    op.drop_index("ix_archive_export_items_artifact_ref", table_name="archive_export_items")
    op.drop_index("ix_archive_export_items_archive_export_id", table_name="archive_export_items")
    op.drop_table("archive_export_items")
    op.drop_index("ix_archive_export_records_set_id", table_name="archive_export_records")
    op.drop_table("archive_export_records")
    op.drop_index("ix_archive_export_sets_deal_closure_set_id", table_name="archive_export_sets")
    op.drop_index("ix_archive_export_sets_deal_id", table_name="archive_export_sets")
    op.drop_table("archive_export_sets")
