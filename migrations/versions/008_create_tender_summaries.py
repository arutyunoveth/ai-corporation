"""create tender summary tables"""

from alembic import op
import sqlalchemy as sa

revision = "008_create_tender_summaries"
down_revision = "007_create_document_ingestion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tender_summaries",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tender_summary_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("intake_id", sa.String(length=64), sa.ForeignKey("tender_intake_records.intake_id"), nullable=False),
        sa.Column("document_set_id", sa.String(length=64), sa.ForeignKey("document_sets.document_set_id"), nullable=False),
        sa.Column("summary_status", sa.Text(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("structured_summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tender_summary_id"),
    )
    op.create_index("ix_tender_summaries_deal_id", "tender_summaries", ["deal_id"])
    op.create_index("ix_tender_summaries_intake_id", "tender_summaries", ["intake_id"])
    op.create_index("ix_tender_summaries_document_set_id", "tender_summaries", ["document_set_id"])
    op.create_index("ix_tender_summaries_summary_status", "tender_summaries", ["summary_status"])

    op.create_table(
        "tender_summary_source_links",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tender_summary_id", sa.String(length=64), sa.ForeignKey("tender_summaries.tender_summary_id"), nullable=False),
        sa.Column("source_object_type", sa.Text(), nullable=False),
        sa.Column("source_object_ref", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_tender_summary_source_links_summary_id",
        "tender_summary_source_links",
        ["tender_summary_id"],
    )
    op.create_index(
        "ix_tender_summary_source_links_object",
        "tender_summary_source_links",
        ["source_object_type", "source_object_ref"],
    )


def downgrade() -> None:
    op.drop_index("ix_tender_summary_source_links_object", table_name="tender_summary_source_links")
    op.drop_index("ix_tender_summary_source_links_summary_id", table_name="tender_summary_source_links")
    op.drop_table("tender_summary_source_links")
    op.drop_index("ix_tender_summaries_summary_status", table_name="tender_summaries")
    op.drop_index("ix_tender_summaries_document_set_id", table_name="tender_summaries")
    op.drop_index("ix_tender_summaries_intake_id", table_name="tender_summaries")
    op.drop_index("ix_tender_summaries_deal_id", table_name="tender_summaries")
    op.drop_table("tender_summaries")
