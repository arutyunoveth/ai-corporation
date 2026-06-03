"""create execution command tables"""

from alembic import op
import sqlalchemy as sa

revision = "037_create_execution_command"
down_revision = "036_create_delivery_launch"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "execution_command_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("execution_command_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "delivery_launch_set_id",
            sa.String(length=64),
            sa.ForeignKey("delivery_launch_sets.delivery_launch_set_id"),
            nullable=False,
        ),
        sa.Column("execution_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("execution_command_set_id"),
    )
    op.create_index("ix_execution_command_sets_deal_id", "execution_command_sets", ["deal_id"])
    op.create_index(
        "ix_execution_command_sets_delivery_launch_set_id",
        "execution_command_sets",
        ["delivery_launch_set_id"],
    )

    op.create_table(
        "execution_command_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("execution_command_id", sa.String(length=64), nullable=False),
        sa.Column(
            "execution_command_set_id",
            sa.String(length=64),
            sa.ForeignKey("execution_command_sets.execution_command_set_id"),
            nullable=False,
        ),
        sa.Column("current_phase", sa.Text(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("execution_command_id"),
    )
    op.create_index("ix_execution_command_records_set_id", "execution_command_records", ["execution_command_set_id"])

    op.create_table(
        "execution_command_bindings",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "execution_command_set_id",
            sa.String(length=64),
            sa.ForeignKey("execution_command_sets.execution_command_set_id"),
            nullable=False,
        ),
        sa.Column("source_object_type", sa.String(length=32), nullable=False),
        sa.Column("source_object_ref", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_execution_command_bindings_execution_command_set_id",
        "execution_command_bindings",
        ["execution_command_set_id"],
    )
    op.create_index(
        "ix_execution_command_bindings_source_object_ref",
        "execution_command_bindings",
        ["source_object_ref"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_execution_command_bindings_source_object_ref",
        table_name="execution_command_bindings",
    )
    op.drop_index(
        "ix_execution_command_bindings_execution_command_set_id",
        table_name="execution_command_bindings",
    )
    op.drop_table("execution_command_bindings")
    op.drop_index("ix_execution_command_records_set_id", table_name="execution_command_records")
    op.drop_table("execution_command_records")
    op.drop_index("ix_execution_command_sets_delivery_launch_set_id", table_name="execution_command_sets")
    op.drop_index("ix_execution_command_sets_deal_id", table_name="execution_command_sets")
    op.drop_table("execution_command_sets")
