"""create execution ledger tables"""

from alembic import op
import sqlalchemy as sa

revision = "056_create_execution_ledger"
down_revision = "055_create_operator_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "execution_ledger_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("execution_ledger_set_id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_ref", sa.String(length=128), nullable=False),
        sa.Column("ledger_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("execution_ledger_set_id"),
    )
    op.create_index("ix_execution_ledger_sets_scope_type", "execution_ledger_sets", ["scope_type"])
    op.create_index("ix_execution_ledger_sets_scope_ref", "execution_ledger_sets", ["scope_ref"])

    op.create_table(
        "execution_ledger_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("execution_ledger_id", sa.String(length=64), nullable=False),
        sa.Column(
            "execution_ledger_set_id",
            sa.String(length=64),
            sa.ForeignKey("execution_ledger_sets.execution_ledger_set_id"),
            nullable=False,
        ),
        sa.Column("action_queue_id", sa.String(length=64), nullable=False),
        sa.Column("integration_task_id", sa.String(length=64), nullable=False),
        sa.Column("execution_status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("execution_ledger_id"),
    )
    op.create_index("ix_execution_ledger_records_set_id", "execution_ledger_records", ["execution_ledger_set_id"])
    op.create_index(
        "ix_execution_ledger_records_action_queue_id",
        "execution_ledger_records",
        ["action_queue_id"],
    )
    op.create_index(
        "ix_execution_ledger_records_integration_task_id",
        "execution_ledger_records",
        ["integration_task_id"],
    )
    op.create_index(
        "ix_execution_ledger_records_execution_status",
        "execution_ledger_records",
        ["execution_status"],
    )

    op.create_table(
        "execution_result_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "execution_ledger_id",
            sa.String(length=64),
            sa.ForeignKey("execution_ledger_records.execution_ledger_id"),
            nullable=False,
        ),
        sa.Column("result_code", sa.String(length=64), nullable=False),
        sa.Column("result_summary", sa.Text(), nullable=False),
        sa.Column("artifact_ref", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_execution_result_records_execution_ledger_id",
        "execution_result_records",
        ["execution_ledger_id"],
    )
    op.create_index("ix_execution_result_records_result_code", "execution_result_records", ["result_code"])


def downgrade() -> None:
    op.drop_index("ix_execution_result_records_result_code", table_name="execution_result_records")
    op.drop_index("ix_execution_result_records_execution_ledger_id", table_name="execution_result_records")
    op.drop_table("execution_result_records")
    op.drop_index("ix_execution_ledger_records_execution_status", table_name="execution_ledger_records")
    op.drop_index("ix_execution_ledger_records_integration_task_id", table_name="execution_ledger_records")
    op.drop_index("ix_execution_ledger_records_action_queue_id", table_name="execution_ledger_records")
    op.drop_index("ix_execution_ledger_records_set_id", table_name="execution_ledger_records")
    op.drop_table("execution_ledger_records")
    op.drop_index("ix_execution_ledger_sets_scope_ref", table_name="execution_ledger_sets")
    op.drop_index("ix_execution_ledger_sets_scope_type", table_name="execution_ledger_sets")
    op.drop_table("execution_ledger_sets")
