"""create runtime metadata slices

Revision ID: 086_create_runtime_metadata_slices
Revises: 085_create_runtime_control_trace_ledger
Create Date: 2026-06-06 16:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "086_create_runtime_metadata_slices"
down_revision: str | Sequence[str] | None = "085_create_runtime_control_trace_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runtime_metadata_slices",
        sa.Column("runtime_metadata_slice_id", sa.String(length=64), nullable=False),
        sa.Column("runtime_slice", sa.Text(), nullable=False),
        sa.Column("linked_agent_profile_id", sa.String(length=64), nullable=False),
        sa.Column("linked_prompt_schema_id", sa.String(length=64), nullable=False),
        sa.Column("allowed_runtime_contexts", sa.JSON(), nullable=False),
        sa.Column("forbidden_runtime_contexts", sa.JSON(), nullable=False),
        sa.Column("review_status", sa.Text(), nullable=False),
        sa.Column("trace_refs_json", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["linked_agent_profile_id"], ["agent_registry_records.agent_registry_id"]),
        sa.ForeignKeyConstraint(["linked_prompt_schema_id"], ["prompt_schema_records.prompt_schema_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("runtime_metadata_slice_id"),
    )
    op.create_index(
        "ix_runtime_metadata_slices_runtime_slice",
        "runtime_metadata_slices",
        ["runtime_slice"],
    )
    op.create_index(
        "ix_runtime_metadata_slices_agent_profile",
        "runtime_metadata_slices",
        ["linked_agent_profile_id"],
    )
    op.create_index(
        "ix_runtime_metadata_slices_prompt_schema",
        "runtime_metadata_slices",
        ["linked_prompt_schema_id"],
    )
    op.create_index(
        "ix_runtime_metadata_slices_review_status",
        "runtime_metadata_slices",
        ["review_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_runtime_metadata_slices_review_status", table_name="runtime_metadata_slices")
    op.drop_index("ix_runtime_metadata_slices_prompt_schema", table_name="runtime_metadata_slices")
    op.drop_index("ix_runtime_metadata_slices_agent_profile", table_name="runtime_metadata_slices")
    op.drop_index("ix_runtime_metadata_slices_runtime_slice", table_name="runtime_metadata_slices")
    op.drop_table("runtime_metadata_slices")
