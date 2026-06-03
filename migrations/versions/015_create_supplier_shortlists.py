"""create supplier shortlist tables"""

from alembic import op
import sqlalchemy as sa

revision = "015_create_supplier_shortlists"
down_revision = "014_create_supplier_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplier_shortlists",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("supplier_shortlist_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("intake_id", sa.String(length=64), sa.ForeignKey("tender_intake_records.intake_id"), nullable=False),
        sa.Column("document_set_id", sa.String(length=64), sa.ForeignKey("document_sets.document_set_id"), nullable=False),
        sa.Column("tender_summary_id", sa.String(length=64), sa.ForeignKey("tender_summaries.tender_summary_id"), nullable=False),
        sa.Column("shortlist_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("supplier_shortlist_id"),
    )
    op.create_index("ix_supplier_shortlists_deal_id", "supplier_shortlists", ["deal_id"])
    op.create_index("ix_supplier_shortlists_tender_summary_id", "supplier_shortlists", ["tender_summary_id"])

    op.create_table(
        "supplier_shortlist_rows",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "supplier_shortlist_id",
            sa.String(length=64),
            sa.ForeignKey("supplier_shortlists.supplier_shortlist_id"),
            nullable=False,
        ),
        sa.Column("supplier_id", sa.String(length=64), sa.ForeignKey("supplier_profiles.supplier_id"), nullable=False),
        sa.Column("rank_order", sa.Integer(), nullable=False),
        sa.Column("inclusion_reason", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("supplier_shortlist_id", "supplier_id", name="uq_supplier_shortlist_rows_supplier"),
    )
    op.create_index("ix_supplier_shortlist_rows_shortlist_id", "supplier_shortlist_rows", ["supplier_shortlist_id"])
    op.create_index("ix_supplier_shortlist_rows_supplier_id", "supplier_shortlist_rows", ["supplier_id"])


def downgrade() -> None:
    op.drop_index("ix_supplier_shortlist_rows_supplier_id", table_name="supplier_shortlist_rows")
    op.drop_index("ix_supplier_shortlist_rows_shortlist_id", table_name="supplier_shortlist_rows")
    op.drop_table("supplier_shortlist_rows")
    op.drop_index("ix_supplier_shortlists_tender_summary_id", table_name="supplier_shortlists")
    op.drop_index("ix_supplier_shortlists_deal_id", table_name="supplier_shortlists")
    op.drop_table("supplier_shortlists")
