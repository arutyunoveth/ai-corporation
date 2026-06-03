"""create delivery milestone tables"""

from alembic import op
import sqlalchemy as sa

revision = "038_create_delivery_milestones"
down_revision = "037_create_execution_command"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "delivery_milestone_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("delivery_milestone_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "execution_command_set_id",
            sa.String(length=64),
            sa.ForeignKey("execution_command_sets.execution_command_set_id"),
            nullable=False,
        ),
        sa.Column("milestone_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("delivery_milestone_set_id"),
    )
    op.create_index("ix_delivery_milestone_sets_deal_id", "delivery_milestone_sets", ["deal_id"])
    op.create_index(
        "ix_delivery_milestone_sets_execution_command_set_id",
        "delivery_milestone_sets",
        ["execution_command_set_id"],
    )

    op.create_table(
        "delivery_milestone_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("delivery_milestone_id", sa.String(length=64), nullable=False),
        sa.Column(
            "delivery_milestone_set_id",
            sa.String(length=64),
            sa.ForeignKey("delivery_milestone_sets.delivery_milestone_set_id"),
            nullable=False,
        ),
        sa.Column("milestone_code", sa.String(length=64), nullable=False),
        sa.Column("milestone_name", sa.Text(), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("milestone_state", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("delivery_milestone_id"),
    )
    op.create_index("ix_delivery_milestone_records_set_id", "delivery_milestone_records", ["delivery_milestone_set_id"])
    op.create_index(
        "ix_delivery_milestone_records_milestone_code",
        "delivery_milestone_records",
        ["milestone_code"],
    )

    op.create_table(
        "delivery_milestone_events",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("delivery_milestone_event_id", sa.String(length=64), nullable=False),
        sa.Column(
            "delivery_milestone_id",
            sa.String(length=64),
            sa.ForeignKey("delivery_milestone_records.delivery_milestone_id"),
            nullable=False,
        ),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("delivery_milestone_event_id"),
    )
    op.create_index(
        "ix_delivery_milestone_events_delivery_milestone_id",
        "delivery_milestone_events",
        ["delivery_milestone_id"],
    )
    op.create_index(
        "ix_delivery_milestone_events_event_timestamp",
        "delivery_milestone_events",
        ["event_timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_delivery_milestone_events_event_timestamp", table_name="delivery_milestone_events")
    op.drop_index(
        "ix_delivery_milestone_events_delivery_milestone_id",
        table_name="delivery_milestone_events",
    )
    op.drop_table("delivery_milestone_events")
    op.drop_index("ix_delivery_milestone_records_milestone_code", table_name="delivery_milestone_records")
    op.drop_index("ix_delivery_milestone_records_set_id", table_name="delivery_milestone_records")
    op.drop_table("delivery_milestone_records")
    op.drop_index(
        "ix_delivery_milestone_sets_execution_command_set_id",
        table_name="delivery_milestone_sets",
    )
    op.drop_index("ix_delivery_milestone_sets_deal_id", table_name="delivery_milestone_sets")
    op.drop_table("delivery_milestone_sets")
