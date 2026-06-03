"""create supplier communication tables"""

from alembic import op
import sqlalchemy as sa

revision = "017_create_supplier_communications"
down_revision = "016_create_rfq_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplier_communication_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("supplier_communication_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("rfq_batch_id", sa.String(length=64), sa.ForeignKey("rfq_batches.rfq_batch_id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("supplier_communication_set_id"),
    )
    op.create_index("ix_supplier_communication_sets_deal_id", "supplier_communication_sets", ["deal_id"])
    op.create_index("ix_supplier_communication_sets_rfq_batch_id", "supplier_communication_sets", ["rfq_batch_id"])

    op.create_table(
        "supplier_communication_threads",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("supplier_thread_id", sa.String(length=64), nullable=False),
        sa.Column(
            "supplier_communication_set_id",
            sa.String(length=64),
            sa.ForeignKey("supplier_communication_sets.supplier_communication_set_id"),
            nullable=False,
        ),
        sa.Column("supplier_id", sa.String(length=64), sa.ForeignKey("supplier_profiles.supplier_id"), nullable=False),
        sa.Column("rfq_id", sa.String(length=64), sa.ForeignKey("rfq_records.rfq_id"), nullable=False),
        sa.Column("thread_status", sa.Text(), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("supplier_thread_id"),
    )
    op.create_index("ix_supplier_communication_threads_set_id", "supplier_communication_threads", ["supplier_communication_set_id"])
    op.create_index("ix_supplier_communication_threads_supplier_id", "supplier_communication_threads", ["supplier_id"])
    op.create_index("ix_supplier_communication_threads_rfq_id", "supplier_communication_threads", ["rfq_id"])

    op.create_table(
        "supplier_message_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("supplier_message_id", sa.String(length=64), nullable=False),
        sa.Column(
            "supplier_thread_id",
            sa.String(length=64),
            sa.ForeignKey("supplier_communication_threads.supplier_thread_id"),
            nullable=False,
        ),
        sa.Column("direction", sa.String(length=32), nullable=False),
        sa.Column("message_subject", sa.Text(), nullable=True),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("linked_artifact_ref", sa.String(length=64), sa.ForeignKey("document_artifacts.artifact_ref"), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("supplier_message_id"),
    )
    op.create_index("ix_supplier_message_records_thread_id", "supplier_message_records", ["supplier_thread_id"])
    op.create_index("ix_supplier_message_records_direction", "supplier_message_records", ["direction"])


def downgrade() -> None:
    op.drop_index("ix_supplier_message_records_direction", table_name="supplier_message_records")
    op.drop_index("ix_supplier_message_records_thread_id", table_name="supplier_message_records")
    op.drop_table("supplier_message_records")
    op.drop_index("ix_supplier_communication_threads_rfq_id", table_name="supplier_communication_threads")
    op.drop_index("ix_supplier_communication_threads_supplier_id", table_name="supplier_communication_threads")
    op.drop_index("ix_supplier_communication_threads_set_id", table_name="supplier_communication_threads")
    op.drop_table("supplier_communication_threads")
    op.drop_index("ix_supplier_communication_sets_rfq_batch_id", table_name="supplier_communication_sets")
    op.drop_index("ix_supplier_communication_sets_deal_id", table_name="supplier_communication_sets")
    op.drop_table("supplier_communication_sets")
