"""create workflow run tables"""

from alembic import op
import sqlalchemy as sa

revision = "048_create_workflow_runs"
down_revision = "047_create_learning_automation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_run_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("workflow_run_set_id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_ref", sa.String(length=128), nullable=False),
        sa.Column("workflow_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workflow_run_set_id"),
    )
    op.create_index("ix_workflow_run_sets_scope_type", "workflow_run_sets", ["scope_type"])
    op.create_index("ix_workflow_run_sets_scope_ref", "workflow_run_sets", ["scope_ref"])

    op.create_table(
        "workflow_run_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("workflow_run_id", sa.String(length=64), nullable=False),
        sa.Column(
            "workflow_run_set_id",
            sa.String(length=64),
            sa.ForeignKey("workflow_run_sets.workflow_run_set_id"),
            nullable=False,
        ),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("current_phase", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workflow_run_id"),
    )
    op.create_index("ix_workflow_run_records_set_id", "workflow_run_records", ["workflow_run_set_id"])

    op.create_table(
        "workflow_step_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("workflow_step_id", sa.String(length=64), nullable=False),
        sa.Column(
            "workflow_run_id",
            sa.String(length=64),
            sa.ForeignKey("workflow_run_records.workflow_run_id"),
            nullable=False,
        ),
        sa.Column("step_code", sa.String(length=64), nullable=False),
        sa.Column("step_type", sa.Text(), nullable=False),
        sa.Column("step_status", sa.Text(), nullable=False),
        sa.Column("depends_on_step_ref", sa.String(length=64), nullable=True),
        sa.Column("source_ref", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workflow_step_id"),
    )
    op.create_index("ix_workflow_step_records_run_id", "workflow_step_records", ["workflow_run_id"])
    op.create_index("ix_workflow_step_records_step_code", "workflow_step_records", ["step_code"])


def downgrade() -> None:
    op.drop_index("ix_workflow_step_records_step_code", table_name="workflow_step_records")
    op.drop_index("ix_workflow_step_records_run_id", table_name="workflow_step_records")
    op.drop_table("workflow_step_records")
    op.drop_index("ix_workflow_run_records_set_id", table_name="workflow_run_records")
    op.drop_table("workflow_run_records")
    op.drop_index("ix_workflow_run_sets_scope_ref", table_name="workflow_run_sets")
    op.drop_index("ix_workflow_run_sets_scope_type", table_name="workflow_run_sets")
    op.drop_table("workflow_run_sets")
