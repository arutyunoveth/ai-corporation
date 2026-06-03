"""create shipping acceptance tables"""

from alembic import op
import sqlalchemy as sa

revision = "040_create_shipping_acceptance"
down_revision = "039_create_supplier_fulfillment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shipping_acceptance_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("shipping_acceptance_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "execution_command_set_id",
            sa.String(length=64),
            sa.ForeignKey("execution_command_sets.execution_command_set_id"),
            nullable=False,
        ),
        sa.Column("shipping_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("shipping_acceptance_set_id"),
    )
    op.create_index("ix_shipping_acceptance_sets_deal_id", "shipping_acceptance_sets", ["deal_id"])
    op.create_index(
        "ix_shipping_acceptance_sets_execution_command_set_id",
        "shipping_acceptance_sets",
        ["execution_command_set_id"],
    )

    op.create_table(
        "shipping_acceptance_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("shipping_acceptance_id", sa.String(length=64), nullable=False),
        sa.Column(
            "shipping_acceptance_set_id",
            sa.String(length=64),
            sa.ForeignKey("shipping_acceptance_sets.shipping_acceptance_set_id"),
            nullable=False,
        ),
        sa.Column("shipment_ref", sa.String(length=128), nullable=True),
        sa.Column("acceptance_ref", sa.String(length=128), nullable=True),
        sa.Column("current_state", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("shipping_acceptance_id"),
    )
    op.create_index("ix_shipping_acceptance_records_set_id", "shipping_acceptance_records", ["shipping_acceptance_set_id"])
    op.create_index("ix_shipping_acceptance_records_shipment_ref", "shipping_acceptance_records", ["shipment_ref"])

    op.create_table(
        "shipping_acceptance_events",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("shipping_acceptance_event_id", sa.String(length=64), nullable=False),
        sa.Column(
            "shipping_acceptance_id",
            sa.String(length=64),
            sa.ForeignKey("shipping_acceptance_records.shipping_acceptance_id"),
            nullable=False,
        ),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("shipping_acceptance_event_id"),
    )
    op.create_index(
        "ix_shipping_acceptance_events_shipping_acceptance_id",
        "shipping_acceptance_events",
        ["shipping_acceptance_id"],
    )
    op.create_index(
        "ix_shipping_acceptance_events_event_timestamp",
        "shipping_acceptance_events",
        ["event_timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_shipping_acceptance_events_event_timestamp", table_name="shipping_acceptance_events")
    op.drop_index(
        "ix_shipping_acceptance_events_shipping_acceptance_id",
        table_name="shipping_acceptance_events",
    )
    op.drop_table("shipping_acceptance_events")
    op.drop_index("ix_shipping_acceptance_records_shipment_ref", table_name="shipping_acceptance_records")
    op.drop_index("ix_shipping_acceptance_records_set_id", table_name="shipping_acceptance_records")
    op.drop_table("shipping_acceptance_records")
    op.drop_index(
        "ix_shipping_acceptance_sets_execution_command_set_id",
        table_name="shipping_acceptance_sets",
    )
    op.drop_index("ix_shipping_acceptance_sets_deal_id", table_name="shipping_acceptance_sets")
    op.drop_table("shipping_acceptance_sets")
