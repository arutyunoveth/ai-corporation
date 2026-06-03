"""create quote repository tables"""

from alembic import op
import sqlalchemy as sa

revision = "018_create_quote_repository"
down_revision = "017_create_supplier_communications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quote_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("quote_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("rfq_batch_id", sa.String(length=64), sa.ForeignKey("rfq_batches.rfq_batch_id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("quote_set_id"),
    )
    op.create_index("ix_quote_sets_deal_id", "quote_sets", ["deal_id"])
    op.create_index("ix_quote_sets_rfq_batch_id", "quote_sets", ["rfq_batch_id"])

    op.create_table(
        "quote_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("quote_id", sa.String(length=64), nullable=False),
        sa.Column("quote_set_id", sa.String(length=64), sa.ForeignKey("quote_sets.quote_set_id"), nullable=False),
        sa.Column("supplier_id", sa.String(length=64), sa.ForeignKey("supplier_profiles.supplier_id"), nullable=False),
        sa.Column("rfq_id", sa.String(length=64), sa.ForeignKey("rfq_records.rfq_id"), nullable=False),
        sa.Column(
            "supplier_thread_id",
            sa.String(length=64),
            sa.ForeignKey("supplier_communication_threads.supplier_thread_id"),
            nullable=False,
        ),
        sa.Column("quote_status", sa.Text(), nullable=False),
        sa.Column("quoted_amount", sa.Float(), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("quoted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("quote_id"),
    )
    op.create_index("ix_quote_records_set_id", "quote_records", ["quote_set_id"])
    op.create_index("ix_quote_records_supplier_id", "quote_records", ["supplier_id"])
    op.create_index("ix_quote_records_rfq_id", "quote_records", ["rfq_id"])

    op.create_table(
        "quote_artifact_bindings",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("quote_id", sa.String(length=64), sa.ForeignKey("quote_records.quote_id"), nullable=False),
        sa.Column("artifact_ref", sa.String(length=64), sa.ForeignKey("document_artifacts.artifact_ref"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_quote_artifact_bindings_quote_id", "quote_artifact_bindings", ["quote_id"])
    op.create_index("ix_quote_artifact_bindings_artifact_ref", "quote_artifact_bindings", ["artifact_ref"])


def downgrade() -> None:
    op.drop_index("ix_quote_artifact_bindings_artifact_ref", table_name="quote_artifact_bindings")
    op.drop_index("ix_quote_artifact_bindings_quote_id", table_name="quote_artifact_bindings")
    op.drop_table("quote_artifact_bindings")
    op.drop_index("ix_quote_records_rfq_id", table_name="quote_records")
    op.drop_index("ix_quote_records_supplier_id", table_name="quote_records")
    op.drop_index("ix_quote_records_set_id", table_name="quote_records")
    op.drop_table("quote_records")
    op.drop_index("ix_quote_sets_rfq_batch_id", table_name="quote_sets")
    op.drop_index("ix_quote_sets_deal_id", table_name="quote_sets")
    op.drop_table("quote_sets")
