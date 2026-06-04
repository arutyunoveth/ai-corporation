"""create integration task tables"""

from alembic import op
import sqlalchemy as sa

revision = "054_create_integration_tasks"
down_revision = "053_create_action_queue"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_task_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("integration_task_set_id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_ref", sa.String(length=128), nullable=False),
        sa.Column("task_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("integration_task_set_id"),
    )
    op.create_index("ix_integration_task_sets_scope_type", "integration_task_sets", ["scope_type"])
    op.create_index("ix_integration_task_sets_scope_ref", "integration_task_sets", ["scope_ref"])

    op.create_table(
        "integration_task_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("integration_task_id", sa.String(length=64), nullable=False),
        sa.Column(
            "integration_task_set_id",
            sa.String(length=64),
            sa.ForeignKey("integration_task_sets.integration_task_set_id"),
            nullable=False,
        ),
        sa.Column("connector_registry_id", sa.String(length=64), nullable=False),
        sa.Column("action_queue_id", sa.String(length=64), nullable=False),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column("task_payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("integration_task_id"),
    )
    op.create_index("ix_integration_task_records_set_id", "integration_task_records", ["integration_task_set_id"])
    op.create_index(
        "ix_integration_task_records_connector_registry_id",
        "integration_task_records",
        ["connector_registry_id"],
    )
    op.create_index(
        "ix_integration_task_records_action_queue_id",
        "integration_task_records",
        ["action_queue_id"],
    )
    op.create_index("ix_integration_task_records_task_type", "integration_task_records", ["task_type"])

    op.create_table(
        "integration_task_bindings",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "integration_task_id",
            sa.String(length=64),
            sa.ForeignKey("integration_task_records.integration_task_id"),
            nullable=False,
        ),
        sa.Column("source_ref", sa.String(length=128), nullable=False),
        sa.Column("binding_type", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_integration_task_bindings_integration_task_id",
        "integration_task_bindings",
        ["integration_task_id"],
    )
    op.create_index("ix_integration_task_bindings_binding_type", "integration_task_bindings", ["binding_type"])


def downgrade() -> None:
    op.drop_index("ix_integration_task_bindings_binding_type", table_name="integration_task_bindings")
    op.drop_index("ix_integration_task_bindings_integration_task_id", table_name="integration_task_bindings")
    op.drop_table("integration_task_bindings")
    op.drop_index("ix_integration_task_records_task_type", table_name="integration_task_records")
    op.drop_index("ix_integration_task_records_action_queue_id", table_name="integration_task_records")
    op.drop_index("ix_integration_task_records_connector_registry_id", table_name="integration_task_records")
    op.drop_index("ix_integration_task_records_set_id", table_name="integration_task_records")
    op.drop_table("integration_task_records")
    op.drop_index("ix_integration_task_sets_scope_ref", table_name="integration_task_sets")
    op.drop_index("ix_integration_task_sets_scope_type", table_name="integration_task_sets")
    op.drop_table("integration_task_sets")
