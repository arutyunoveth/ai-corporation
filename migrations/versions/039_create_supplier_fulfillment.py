"""create supplier fulfillment tables"""

from alembic import op
import sqlalchemy as sa

revision = "039_create_supplier_fulfillment"
down_revision = "038_create_delivery_milestones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplier_fulfillment_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("supplier_fulfillment_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "execution_command_set_id",
            sa.String(length=64),
            sa.ForeignKey("execution_command_sets.execution_command_set_id"),
            nullable=False,
        ),
        sa.Column("fulfillment_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("supplier_fulfillment_set_id"),
    )
    op.create_index("ix_supplier_fulfillment_sets_deal_id", "supplier_fulfillment_sets", ["deal_id"])
    op.create_index(
        "ix_supplier_fulfillment_sets_execution_command_set_id",
        "supplier_fulfillment_sets",
        ["execution_command_set_id"],
    )

    op.create_table(
        "supplier_fulfillment_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("supplier_fulfillment_id", sa.String(length=64), nullable=False),
        sa.Column(
            "supplier_fulfillment_set_id",
            sa.String(length=64),
            sa.ForeignKey("supplier_fulfillment_sets.supplier_fulfillment_set_id"),
            nullable=False,
        ),
        sa.Column("supplier_id", sa.String(length=64), sa.ForeignKey("supplier_profiles.supplier_id"), nullable=False),
        sa.Column("fulfillment_state", sa.Text(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("supplier_fulfillment_id"),
    )
    op.create_index("ix_supplier_fulfillment_records_set_id", "supplier_fulfillment_records", ["supplier_fulfillment_set_id"])
    op.create_index("ix_supplier_fulfillment_records_supplier_id", "supplier_fulfillment_records", ["supplier_id"])

    op.create_table(
        "supplier_fulfillment_events",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("supplier_fulfillment_event_id", sa.String(length=64), nullable=False),
        sa.Column(
            "supplier_fulfillment_id",
            sa.String(length=64),
            sa.ForeignKey("supplier_fulfillment_records.supplier_fulfillment_id"),
            nullable=False,
        ),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("supplier_fulfillment_event_id"),
    )
    op.create_index(
        "ix_supplier_fulfillment_events_supplier_fulfillment_id",
        "supplier_fulfillment_events",
        ["supplier_fulfillment_id"],
    )
    op.create_index(
        "ix_supplier_fulfillment_events_event_timestamp",
        "supplier_fulfillment_events",
        ["event_timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_supplier_fulfillment_events_event_timestamp", table_name="supplier_fulfillment_events")
    op.drop_index(
        "ix_supplier_fulfillment_events_supplier_fulfillment_id",
        table_name="supplier_fulfillment_events",
    )
    op.drop_table("supplier_fulfillment_events")
    op.drop_index("ix_supplier_fulfillment_records_supplier_id", table_name="supplier_fulfillment_records")
    op.drop_index("ix_supplier_fulfillment_records_set_id", table_name="supplier_fulfillment_records")
    op.drop_table("supplier_fulfillment_records")
    op.drop_index(
        "ix_supplier_fulfillment_sets_execution_command_set_id",
        table_name="supplier_fulfillment_sets",
    )
    op.drop_index("ix_supplier_fulfillment_sets_deal_id", table_name="supplier_fulfillment_sets")
    op.drop_table("supplier_fulfillment_sets")
