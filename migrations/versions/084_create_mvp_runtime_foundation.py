"""create mvp runtime foundation tables

Revision ID: 084_create_mvp_runtime_foundation
Revises: 083_create_launch_visibility
Create Date: 2026-06-06 10:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "084_create_mvp_runtime_foundation"
down_revision: str | Sequence[str] | None = "083_create_launch_visibility"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_registry_sets",
        sa.Column("agent_registry_set_id", sa.String(length=64), nullable=False),
        sa.Column("registry_scope", sa.Text(), nullable=False),
        sa.Column("registry_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_registry_set_id"),
    )
    op.create_index("ix_agent_registry_sets_registry_scope", "agent_registry_sets", ["registry_scope"])

    op.create_table(
        "prompt_schema_library_sets",
        sa.Column("prompt_schema_library_set_id", sa.String(length=64), nullable=False),
        sa.Column("library_scope", sa.Text(), nullable=False),
        sa.Column("library_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prompt_schema_library_set_id"),
    )
    op.create_index("ix_prompt_schema_library_sets_library_scope", "prompt_schema_library_sets", ["library_scope"])

    op.create_table(
        "agent_registry_records",
        sa.Column("agent_registry_id", sa.String(length=64), nullable=False),
        sa.Column("agent_registry_set_id", sa.String(length=64), nullable=False),
        sa.Column("agent_key", sa.String(length=128), nullable=False),
        sa.Column("agent_label", sa.Text(), nullable=False),
        sa.Column("owner_role", sa.Text(), nullable=False),
        sa.Column("reviewer_role", sa.Text(), nullable=False),
        sa.Column("activation_state", sa.Text(), nullable=False),
        sa.Column("approval_reference", sa.Text(), nullable=True),
        sa.Column("allowed_capabilities_json", sa.JSON(), nullable=False),
        sa.Column("blocked_capabilities_json", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["agent_registry_set_id"], ["agent_registry_sets.agent_registry_set_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_registry_id"),
        sa.UniqueConstraint("agent_registry_set_id", "agent_key", name="uq_agent_registry_records_set_key"),
    )
    op.create_index("ix_agent_registry_records_set_id", "agent_registry_records", ["agent_registry_set_id"])
    op.create_index("ix_agent_registry_records_agent_key", "agent_registry_records", ["agent_key"])
    op.create_index("ix_agent_registry_records_activation_state", "agent_registry_records", ["activation_state"])

    op.create_table(
        "prompt_schema_records",
        sa.Column("prompt_schema_id", sa.String(length=64), nullable=False),
        sa.Column("prompt_schema_library_set_id", sa.String(length=64), nullable=False),
        sa.Column("asset_key", sa.String(length=128), nullable=False),
        sa.Column("asset_type", sa.Text(), nullable=False),
        sa.Column("version_tag", sa.String(length=64), nullable=False),
        sa.Column("owner_role", sa.Text(), nullable=False),
        sa.Column("reviewer_role", sa.Text(), nullable=False),
        sa.Column("asset_status", sa.Text(), nullable=False),
        sa.Column("usage_constraints_text", sa.Text(), nullable=False),
        sa.Column("input_schema_ref", sa.Text(), nullable=True),
        sa.Column("output_schema_ref", sa.Text(), nullable=True),
        sa.Column("safety_notes", sa.Text(), nullable=True),
        sa.Column("asset_payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["prompt_schema_library_set_id"],
            ["prompt_schema_library_sets.prompt_schema_library_set_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prompt_schema_id"),
        sa.UniqueConstraint(
            "prompt_schema_library_set_id",
            "asset_key",
            "version_tag",
            name="uq_prompt_schema_records_set_key_version",
        ),
    )
    op.create_index("ix_prompt_schema_records_set_id", "prompt_schema_records", ["prompt_schema_library_set_id"])
    op.create_index("ix_prompt_schema_records_asset_key", "prompt_schema_records", ["asset_key"])
    op.create_index("ix_prompt_schema_records_asset_status", "prompt_schema_records", ["asset_status"])

    op.create_table(
        "agent_prompt_links",
        sa.Column("agent_registry_id", sa.String(length=64), nullable=False),
        sa.Column("prompt_schema_id", sa.String(length=64), nullable=False),
        sa.Column("link_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["agent_registry_id"], ["agent_registry_records.agent_registry_id"]),
        sa.ForeignKeyConstraint(["prompt_schema_id"], ["prompt_schema_records.prompt_schema_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_registry_id", "prompt_schema_id", name="uq_agent_prompt_links_pair"),
    )
    op.create_index("ix_agent_prompt_links_agent_registry_id", "agent_prompt_links", ["agent_registry_id"])
    op.create_index("ix_agent_prompt_links_prompt_schema_id", "agent_prompt_links", ["prompt_schema_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_prompt_links_prompt_schema_id", table_name="agent_prompt_links")
    op.drop_index("ix_agent_prompt_links_agent_registry_id", table_name="agent_prompt_links")
    op.drop_table("agent_prompt_links")
    op.drop_index("ix_prompt_schema_records_asset_status", table_name="prompt_schema_records")
    op.drop_index("ix_prompt_schema_records_asset_key", table_name="prompt_schema_records")
    op.drop_index("ix_prompt_schema_records_set_id", table_name="prompt_schema_records")
    op.drop_table("prompt_schema_records")
    op.drop_index("ix_agent_registry_records_activation_state", table_name="agent_registry_records")
    op.drop_index("ix_agent_registry_records_agent_key", table_name="agent_registry_records")
    op.drop_index("ix_agent_registry_records_set_id", table_name="agent_registry_records")
    op.drop_table("agent_registry_records")
    op.drop_index("ix_prompt_schema_library_sets_library_scope", table_name="prompt_schema_library_sets")
    op.drop_table("prompt_schema_library_sets")
    op.drop_index("ix_agent_registry_sets_registry_scope", table_name="agent_registry_sets")
    op.drop_table("agent_registry_sets")
