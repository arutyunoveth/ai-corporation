"""create runtime control trace ledger

Revision ID: 085_create_runtime_control_trace_ledger
Revises: 084_create_mvp_runtime_foundation
Create Date: 2026-06-06 15:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "085_create_runtime_control_trace_ledger"
down_revision: str | Sequence[str] | None = "084_create_mvp_runtime_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runtime_control_traces",
        sa.Column("runtime_trace_id", sa.String(length=64), nullable=False),
        sa.Column("runtime_slice", sa.Text(), nullable=False),
        sa.Column("source_entity", sa.Text(), nullable=False),
        sa.Column("actor_type", sa.Text(), nullable=False),
        sa.Column("actor_ref", sa.Text(), nullable=False),
        sa.Column("action_type", sa.Text(), nullable=False),
        sa.Column("target_module", sa.Text(), nullable=True),
        sa.Column("target_record_id", sa.Text(), nullable=True),
        sa.Column("prompt_schema_ref", sa.String(length=64), nullable=True),
        sa.Column("agent_profile_ref", sa.String(length=64), nullable=True),
        sa.Column("input_artifact_ref", sa.Text(), nullable=True),
        sa.Column("output_artifact_ref", sa.Text(), nullable=True),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("validation_status", sa.Text(), nullable=False),
        sa.Column("human_review_status", sa.Text(), nullable=False),
        sa.Column("reviewer_operator", sa.Text(), nullable=True),
        sa.Column("final_disposition", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["agent_profile_ref"], ["agent_registry_records.agent_registry_id"]),
        sa.ForeignKeyConstraint(["prompt_schema_ref"], ["prompt_schema_records.prompt_schema_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("runtime_trace_id"),
    )
    op.create_index(
        "ix_runtime_control_traces_runtime_slice",
        "runtime_control_traces",
        ["runtime_slice"],
    )
    op.create_index(
        "ix_runtime_control_traces_action_type",
        "runtime_control_traces",
        ["action_type"],
    )
    op.create_index(
        "ix_runtime_control_traces_prompt_schema_ref",
        "runtime_control_traces",
        ["prompt_schema_ref"],
    )
    op.create_index(
        "ix_runtime_control_traces_agent_profile_ref",
        "runtime_control_traces",
        ["agent_profile_ref"],
    )
    op.create_index(
        "ix_runtime_control_traces_human_review_status",
        "runtime_control_traces",
        ["human_review_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_runtime_control_traces_human_review_status", table_name="runtime_control_traces")
    op.drop_index("ix_runtime_control_traces_agent_profile_ref", table_name="runtime_control_traces")
    op.drop_index("ix_runtime_control_traces_prompt_schema_ref", table_name="runtime_control_traces")
    op.drop_index("ix_runtime_control_traces_action_type", table_name="runtime_control_traces")
    op.drop_index("ix_runtime_control_traces_runtime_slice", table_name="runtime_control_traces")
    op.drop_table("runtime_control_traces")
