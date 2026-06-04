"""create postmortem tables

Revision ID: 080_create_postmortems
Revises: 079_create_deal_closure_reports
Create Date: 2026-06-04 15:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "080_create_postmortems"
down_revision: str | Sequence[str] | None = "079_create_deal_closure_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "postmortem_sets",
        sa.Column("postmortem_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), nullable=False),
        sa.Column("deal_closure_report_set_id", sa.String(length=64), nullable=False),
        sa.Column("incident_register_set_id", sa.String(length=64), nullable=True),
        sa.Column("claim_trigger_set_id", sa.String(length=64), nullable=True),
        sa.Column("kpi_learning_set_id", sa.String(length=64), nullable=True),
        sa.Column("postmortem_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["claim_trigger_set_id"], ["claim_trigger_sets.claim_trigger_set_id"]),
        sa.ForeignKeyConstraint(["deal_closure_report_set_id"], ["deal_closure_report_sets.deal_closure_report_set_id"]),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.deal_id"]),
        sa.ForeignKeyConstraint(["incident_register_set_id"], ["incident_register_sets.incident_register_set_id"]),
        sa.ForeignKeyConstraint(["kpi_learning_set_id"], ["kpi_learning_sets.kpi_learning_set_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("postmortem_set_id"),
    )
    op.create_index("ix_postmortem_sets_deal_id", "postmortem_sets", ["deal_id"])
    op.create_index("ix_postmortem_sets_report_set_id", "postmortem_sets", ["deal_closure_report_set_id"])

    op.create_table(
        "postmortem_records",
        sa.Column("postmortem_id", sa.String(length=64), nullable=False),
        sa.Column("postmortem_set_id", sa.String(length=64), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("root_cause_summary", sa.Text(), nullable=False),
        sa.Column("recommendation_summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["postmortem_set_id"], ["postmortem_sets.postmortem_set_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("postmortem_id"),
    )
    op.create_index("ix_postmortem_records_set_id", "postmortem_records", ["postmortem_set_id"])

    op.create_table(
        "postmortem_findings",
        sa.Column("postmortem_id", sa.String(length=64), nullable=False),
        sa.Column("finding_code", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["postmortem_id"], ["postmortem_records.postmortem_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_postmortem_findings_postmortem_id", "postmortem_findings", ["postmortem_id"])
    op.create_index("ix_postmortem_findings_finding_code", "postmortem_findings", ["finding_code"])

    op.create_table(
        "postmortem_action_items",
        sa.Column("postmortem_id", sa.String(length=64), nullable=False),
        sa.Column("action_code", sa.String(length=64), nullable=False),
        sa.Column("owner_hint", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("action_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["postmortem_id"], ["postmortem_records.postmortem_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_postmortem_action_items_postmortem_id", "postmortem_action_items", ["postmortem_id"])
    op.create_index("ix_postmortem_action_items_action_code", "postmortem_action_items", ["action_code"])


def downgrade() -> None:
    op.drop_index("ix_postmortem_action_items_action_code", table_name="postmortem_action_items")
    op.drop_index("ix_postmortem_action_items_postmortem_id", table_name="postmortem_action_items")
    op.drop_table("postmortem_action_items")
    op.drop_index("ix_postmortem_findings_finding_code", table_name="postmortem_findings")
    op.drop_index("ix_postmortem_findings_postmortem_id", table_name="postmortem_findings")
    op.drop_table("postmortem_findings")
    op.drop_index("ix_postmortem_records_set_id", table_name="postmortem_records")
    op.drop_table("postmortem_records")
    op.drop_index("ix_postmortem_sets_report_set_id", table_name="postmortem_sets")
    op.drop_index("ix_postmortem_sets_deal_id", table_name="postmortem_sets")
    op.drop_table("postmortem_sets")
