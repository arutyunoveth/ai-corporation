"""create rfq tables"""

from alembic import op
import sqlalchemy as sa

revision = "016_create_rfq_tables"
down_revision = "015_create_supplier_shortlists"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rfq_batches",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("rfq_batch_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "supplier_shortlist_id",
            sa.String(length=64),
            sa.ForeignKey("supplier_shortlists.supplier_shortlist_id"),
            nullable=False,
        ),
        sa.Column("batch_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("rfq_batch_id"),
    )
    op.create_index("ix_rfq_batches_deal_id", "rfq_batches", ["deal_id"])
    op.create_index("ix_rfq_batches_supplier_shortlist_id", "rfq_batches", ["supplier_shortlist_id"])

    op.create_table(
        "rfq_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("rfq_id", sa.String(length=64), nullable=False),
        sa.Column("rfq_batch_id", sa.String(length=64), sa.ForeignKey("rfq_batches.rfq_batch_id"), nullable=False),
        sa.Column("supplier_id", sa.String(length=64), sa.ForeignKey("supplier_profiles.supplier_id"), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("rfq_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("rfq_id"),
    )
    op.create_index("ix_rfq_records_batch_id", "rfq_records", ["rfq_batch_id"])
    op.create_index("ix_rfq_records_supplier_id", "rfq_records", ["supplier_id"])

    op.create_table(
        "rfq_artifact_bindings",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("rfq_id", sa.String(length=64), sa.ForeignKey("rfq_records.rfq_id"), nullable=False),
        sa.Column("artifact_ref", sa.String(length=64), sa.ForeignKey("document_artifacts.artifact_ref"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_rfq_artifact_bindings_rfq_id", "rfq_artifact_bindings", ["rfq_id"])
    op.create_index("ix_rfq_artifact_bindings_artifact_ref", "rfq_artifact_bindings", ["artifact_ref"])


def downgrade() -> None:
    op.drop_index("ix_rfq_artifact_bindings_artifact_ref", table_name="rfq_artifact_bindings")
    op.drop_index("ix_rfq_artifact_bindings_rfq_id", table_name="rfq_artifact_bindings")
    op.drop_table("rfq_artifact_bindings")
    op.drop_index("ix_rfq_records_supplier_id", table_name="rfq_records")
    op.drop_index("ix_rfq_records_batch_id", table_name="rfq_records")
    op.drop_table("rfq_records")
    op.drop_index("ix_rfq_batches_supplier_shortlist_id", table_name="rfq_batches")
    op.drop_index("ix_rfq_batches_deal_id", table_name="rfq_batches")
    op.drop_table("rfq_batches")
