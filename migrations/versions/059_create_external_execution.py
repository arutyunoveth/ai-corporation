"""create external execution tables"""

from alembic import op
import sqlalchemy as sa

revision = "059_create_external_execution"
down_revision = "058_create_action_console"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_execution_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("external_execution_set_id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_ref", sa.String(length=128), nullable=False),
        sa.Column("gateway_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("external_execution_set_id"),
    )
    op.create_index("ix_external_execution_sets_scope_type", "external_execution_sets", ["scope_type"])
    op.create_index("ix_external_execution_sets_scope_ref", "external_execution_sets", ["scope_ref"])

    op.create_table(
        "external_execution_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("external_execution_id", sa.String(length=64), nullable=False),
        sa.Column(
            "external_execution_set_id",
            sa.String(length=64),
            sa.ForeignKey("external_execution_sets.external_execution_set_id"),
            nullable=False,
        ),
        sa.Column("integration_task_id", sa.String(length=64), nullable=False),
        sa.Column("execution_ledger_id", sa.String(length=64), nullable=False),
        sa.Column("gateway_action_type", sa.Text(), nullable=False),
        sa.Column("request_payload_json", sa.JSON(), nullable=False),
        sa.Column("execution_status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("external_execution_id"),
    )
    op.create_index("ix_external_execution_records_set_id", "external_execution_records", ["external_execution_set_id"])
    op.create_index(
        "ix_external_execution_records_integration_task_id",
        "external_execution_records",
        ["integration_task_id"],
    )
    op.create_index(
        "ix_external_execution_records_execution_ledger_id",
        "external_execution_records",
        ["execution_ledger_id"],
    )
    op.create_index(
        "ix_external_execution_records_execution_status",
        "external_execution_records",
        ["execution_status"],
    )

    op.create_table(
        "external_execution_results",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "external_execution_id",
            sa.String(length=64),
            sa.ForeignKey("external_execution_records.external_execution_id"),
            nullable=False,
        ),
        sa.Column("result_code", sa.String(length=64), nullable=False),
        sa.Column("result_summary", sa.Text(), nullable=False),
        sa.Column("response_payload_json", sa.JSON(), nullable=False),
        sa.Column("artifact_ref", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_external_execution_results_external_execution_id",
        "external_execution_results",
        ["external_execution_id"],
    )
    op.create_index("ix_external_execution_results_result_code", "external_execution_results", ["result_code"])


def downgrade() -> None:
    op.drop_index("ix_external_execution_results_result_code", table_name="external_execution_results")
    op.drop_index(
        "ix_external_execution_results_external_execution_id",
        table_name="external_execution_results",
    )
    op.drop_table("external_execution_results")
    op.drop_index(
        "ix_external_execution_records_execution_status",
        table_name="external_execution_records",
    )
    op.drop_index(
        "ix_external_execution_records_execution_ledger_id",
        table_name="external_execution_records",
    )
    op.drop_index(
        "ix_external_execution_records_integration_task_id",
        table_name="external_execution_records",
    )
    op.drop_index("ix_external_execution_records_set_id", table_name="external_execution_records")
    op.drop_table("external_execution_records")
    op.drop_index("ix_external_execution_sets_scope_ref", table_name="external_execution_sets")
    op.drop_index("ix_external_execution_sets_scope_type", table_name="external_execution_sets")
    op.drop_table("external_execution_sets")
