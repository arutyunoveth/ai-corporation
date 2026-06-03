"""create payment collection tables"""

from alembic import op
import sqlalchemy as sa

revision = "041_create_payment_collection"
down_revision = "040_create_shipping_acceptance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_collection_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("payment_collection_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "execution_command_set_id",
            sa.String(length=64),
            sa.ForeignKey("execution_command_sets.execution_command_set_id"),
            nullable=False,
        ),
        sa.Column("collection_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("payment_collection_set_id"),
    )
    op.create_index("ix_payment_collection_sets_deal_id", "payment_collection_sets", ["deal_id"])
    op.create_index(
        "ix_payment_collection_sets_execution_command_set_id",
        "payment_collection_sets",
        ["execution_command_set_id"],
    )

    op.create_table(
        "payment_collection_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("payment_collection_id", sa.String(length=64), nullable=False),
        sa.Column(
            "payment_collection_set_id",
            sa.String(length=64),
            sa.ForeignKey("payment_collection_sets.payment_collection_set_id"),
            nullable=False,
        ),
        sa.Column("invoice_ref", sa.String(length=128), nullable=True),
        sa.Column("expected_amount", sa.Float(), nullable=False),
        sa.Column("collected_amount", sa.Float(), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("collection_state", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("payment_collection_id"),
    )
    op.create_index("ix_payment_collection_records_set_id", "payment_collection_records", ["payment_collection_set_id"])
    op.create_index("ix_payment_collection_records_invoice_ref", "payment_collection_records", ["invoice_ref"])

    op.create_table(
        "payment_collection_events",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("payment_collection_event_id", sa.String(length=64), nullable=False),
        sa.Column(
            "payment_collection_id",
            sa.String(length=64),
            sa.ForeignKey("payment_collection_records.payment_collection_id"),
            nullable=False,
        ),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("payment_collection_event_id"),
    )
    op.create_index(
        "ix_payment_collection_events_payment_collection_id",
        "payment_collection_events",
        ["payment_collection_id"],
    )
    op.create_index(
        "ix_payment_collection_events_event_timestamp",
        "payment_collection_events",
        ["event_timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_payment_collection_events_event_timestamp", table_name="payment_collection_events")
    op.drop_index(
        "ix_payment_collection_events_payment_collection_id",
        table_name="payment_collection_events",
    )
    op.drop_table("payment_collection_events")
    op.drop_index("ix_payment_collection_records_invoice_ref", table_name="payment_collection_records")
    op.drop_index("ix_payment_collection_records_set_id", table_name="payment_collection_records")
    op.drop_table("payment_collection_records")
    op.drop_index(
        "ix_payment_collection_sets_execution_command_set_id",
        table_name="payment_collection_sets",
    )
    op.drop_index("ix_payment_collection_sets_deal_id", table_name="payment_collection_sets")
    op.drop_table("payment_collection_sets")
