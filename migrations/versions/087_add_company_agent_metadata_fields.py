"""add company agent metadata fields to agent_registry_records

Revision ID: 087_add_company_agent_metadata_fields
Revises: 086_create_runtime_metadata_slices
Create Date: 2026-06-18 12:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "087_add_company_agent_metadata_fields"
down_revision: str | Sequence[str] | None = "086_create_runtime_metadata_slices"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("agent_registry_records", sa.Column("agent_scope", sa.String(length=64), nullable=True))
    op.add_column("agent_registry_records", sa.Column("agent_kind", sa.String(length=64), nullable=True))
    op.add_column("agent_registry_records", sa.Column("reports_to", sa.String(length=128), nullable=True))
    op.add_column("agent_registry_records", sa.Column("data_policy", sa.String(length=64), nullable=True))
    op.add_column("agent_registry_records", sa.Column("runtime_mode", sa.String(length=64), nullable=True))
    op.add_column("agent_registry_records", sa.Column("model_tier", sa.String(length=64), nullable=True))
    op.add_column("agent_registry_records", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "agent_registry_records",
        sa.Column("responsibilities_json", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "agent_registry_records",
        sa.Column("inputs_json", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "agent_registry_records",
        sa.Column("outputs_json", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "agent_registry_records",
        sa.Column("escalation_rules_json", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "agent_registry_records",
        sa.Column("forbidden_actions_json", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.create_index("ix_agent_registry_records_agent_scope", "agent_registry_records", ["agent_scope"])


def downgrade() -> None:
    op.drop_index("ix_agent_registry_records_agent_scope", table_name="agent_registry_records")
    op.drop_column("agent_registry_records", "forbidden_actions_json")
    op.drop_column("agent_registry_records", "escalation_rules_json")
    op.drop_column("agent_registry_records", "outputs_json")
    op.drop_column("agent_registry_records", "inputs_json")
    op.drop_column("agent_registry_records", "responsibilities_json")
    op.drop_column("agent_registry_records", "description")
    op.drop_column("agent_registry_records", "model_tier")
    op.drop_column("agent_registry_records", "runtime_mode")
    op.drop_column("agent_registry_records", "data_policy")
    op.drop_column("agent_registry_records", "reports_to")
    op.drop_column("agent_registry_records", "agent_kind")
    op.drop_column("agent_registry_records", "agent_scope")
