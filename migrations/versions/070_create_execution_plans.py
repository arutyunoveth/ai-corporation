"""create execution plan tables

Revision ID: 070_create_execution_plans
Revises: 069_create_supplier_contracts
Create Date: 2026-06-04 09:35:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "070_create_execution_plans"
down_revision: str | Sequence[str] | None = "069_create_supplier_contracts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "execution_plan_sets",
        sa.Column("execution_plan_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), nullable=False),
        sa.Column("plan_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.deal_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_plan_set_id"),
    )
    op.create_index("ix_execution_plan_sets_deal_id", "execution_plan_sets", ["deal_id"])

    op.create_table(
        "execution_plan_records",
        sa.Column("execution_plan_id", sa.String(length=64), nullable=False),
        sa.Column("execution_plan_set_id", sa.String(length=64), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("baseline_manifest_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["execution_plan_set_id"], ["execution_plan_sets.execution_plan_set_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_plan_id"),
    )
    op.create_index("ix_execution_plan_records_set_id", "execution_plan_records", ["execution_plan_set_id"])

    op.create_table(
        "execution_plan_milestones",
        sa.Column("execution_plan_milestone_id", sa.String(length=64), nullable=False),
        sa.Column("execution_plan_id", sa.String(length=64), nullable=False),
        sa.Column("milestone_code", sa.String(length=64), nullable=False),
        sa.Column("milestone_name", sa.Text(), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("milestone_state", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["execution_plan_id"], ["execution_plan_records.execution_plan_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_plan_milestone_id"),
    )
    op.create_index("ix_execution_plan_milestones_plan_id", "execution_plan_milestones", ["execution_plan_id"])
    op.create_index(
        "ix_execution_plan_milestones_milestone_code",
        "execution_plan_milestones",
        ["milestone_code"],
    )

    op.create_table(
        "execution_plan_assumptions",
        sa.Column("execution_plan_id", sa.String(length=64), nullable=False),
        sa.Column("assumption_code", sa.String(length=64), nullable=False),
        sa.Column("assumption_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["execution_plan_id"], ["execution_plan_records.execution_plan_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_execution_plan_assumptions_plan_id", "execution_plan_assumptions", ["execution_plan_id"])
    op.create_index("ix_execution_plan_assumptions_code", "execution_plan_assumptions", ["assumption_code"])


def downgrade() -> None:
    op.drop_index("ix_execution_plan_assumptions_code", table_name="execution_plan_assumptions")
    op.drop_index("ix_execution_plan_assumptions_plan_id", table_name="execution_plan_assumptions")
    op.drop_table("execution_plan_assumptions")
    op.drop_index("ix_execution_plan_milestones_milestone_code", table_name="execution_plan_milestones")
    op.drop_index("ix_execution_plan_milestones_plan_id", table_name="execution_plan_milestones")
    op.drop_table("execution_plan_milestones")
    op.drop_index("ix_execution_plan_records_set_id", table_name="execution_plan_records")
    op.drop_table("execution_plan_records")
    op.drop_index("ix_execution_plan_sets_deal_id", table_name="execution_plan_sets")
    op.drop_table("execution_plan_sets")
