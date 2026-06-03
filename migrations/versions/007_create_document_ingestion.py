"""create document ingestion tables"""

from alembic import op
import sqlalchemy as sa

revision = "007_create_document_ingestion"
down_revision = "006_create_tender_intake"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("document_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("intake_id", sa.String(length=64), sa.ForeignKey("tender_intake_records.intake_id"), nullable=False),
        sa.Column("set_type", sa.Text(), nullable=False),
        sa.Column("ingestion_status", sa.Text(), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_set_id"),
    )
    op.create_index("ix_document_sets_deal_id", "document_sets", ["deal_id"])
    op.create_index("ix_document_sets_intake_id", "document_sets", ["intake_id"])
    op.create_index("ix_document_sets_ingestion_status", "document_sets", ["ingestion_status"])

    op.create_table(
        "document_set_items",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("document_set_id", sa.String(length=64), sa.ForeignKey("document_sets.document_set_id"), nullable=False),
        sa.Column("artifact_ref", sa.String(length=64), sa.ForeignKey("document_artifacts.artifact_ref"), nullable=False),
        sa.Column("item_role", sa.Text(), nullable=False),
        sa.Column("source_file_name", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_set_id", "artifact_ref", name="uq_document_set_items_set_artifact"),
    )
    op.create_index("ix_document_set_items_document_set_id", "document_set_items", ["document_set_id"])
    op.create_index("ix_document_set_items_artifact_ref", "document_set_items", ["artifact_ref"])
    op.create_index("ix_document_set_items_item_role", "document_set_items", ["item_role"])

    op.create_table(
        "document_ingestion_runs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("ingestion_run_id", sa.String(length=64), nullable=False),
        sa.Column("document_set_id", sa.String(length=64), sa.ForeignKey("document_sets.document_set_id"), nullable=False),
        sa.Column("run_status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("ingestion_run_id"),
    )
    op.create_index("ix_document_ingestion_runs_document_set_id", "document_ingestion_runs", ["document_set_id"])
    op.create_index("ix_document_ingestion_runs_run_status", "document_ingestion_runs", ["run_status"])


def downgrade() -> None:
    op.drop_index("ix_document_ingestion_runs_run_status", table_name="document_ingestion_runs")
    op.drop_index("ix_document_ingestion_runs_document_set_id", table_name="document_ingestion_runs")
    op.drop_table("document_ingestion_runs")
    op.drop_index("ix_document_set_items_item_role", table_name="document_set_items")
    op.drop_index("ix_document_set_items_artifact_ref", table_name="document_set_items")
    op.drop_index("ix_document_set_items_document_set_id", table_name="document_set_items")
    op.drop_table("document_set_items")
    op.drop_index("ix_document_sets_ingestion_status", table_name="document_sets")
    op.drop_index("ix_document_sets_intake_id", table_name="document_sets")
    op.drop_index("ix_document_sets_deal_id", table_name="document_sets")
    op.drop_table("document_sets")

