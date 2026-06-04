"""create deal closure report tables

Revision ID: 079_create_deal_closure_reports
Revises: 078_create_claim_triggers
Create Date: 2026-06-04 15:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "079_create_deal_closure_reports"
down_revision: str | Sequence[str] | None = "078_create_claim_triggers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deal_closure_report_sets",
        sa.Column("deal_closure_report_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), nullable=False),
        sa.Column("deal_closure_set_id", sa.String(length=64), nullable=False),
        sa.Column("acceptance_control_set_id", sa.String(length=64), nullable=True),
        sa.Column("closing_docs_set_id", sa.String(length=64), nullable=True),
        sa.Column("payment_tracking_set_id", sa.String(length=64), nullable=True),
        sa.Column("claim_trigger_set_id", sa.String(length=64), nullable=True),
        sa.Column("report_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["acceptance_control_set_id"], ["acceptance_control_sets.acceptance_control_set_id"]),
        sa.ForeignKeyConstraint(["claim_trigger_set_id"], ["claim_trigger_sets.claim_trigger_set_id"]),
        sa.ForeignKeyConstraint(["closing_docs_set_id"], ["closing_docs_sets.closing_docs_set_id"]),
        sa.ForeignKeyConstraint(["deal_closure_set_id"], ["deal_closure_sets.deal_closure_set_id"]),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.deal_id"]),
        sa.ForeignKeyConstraint(["payment_tracking_set_id"], ["payment_tracking_sets.payment_tracking_set_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deal_closure_report_set_id"),
    )
    op.create_index("ix_deal_closure_report_sets_deal_id", "deal_closure_report_sets", ["deal_id"])
    op.create_index(
        "ix_deal_closure_report_sets_closure_set_id",
        "deal_closure_report_sets",
        ["deal_closure_set_id"],
    )

    op.create_table(
        "deal_closure_report_records",
        sa.Column("deal_closure_report_id", sa.String(length=64), nullable=False),
        sa.Column("deal_closure_report_set_id", sa.String(length=64), nullable=False),
        sa.Column("report_code", sa.String(length=64), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("closure_health", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["deal_closure_report_set_id"],
            ["deal_closure_report_sets.deal_closure_report_set_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deal_closure_report_id"),
    )
    op.create_index(
        "ix_deal_closure_report_records_set_id",
        "deal_closure_report_records",
        ["deal_closure_report_set_id"],
    )
    op.create_index(
        "ix_deal_closure_report_records_report_code",
        "deal_closure_report_records",
        ["report_code"],
    )

    op.create_table(
        "deal_closure_report_links",
        sa.Column("deal_closure_report_id", sa.String(length=64), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["deal_closure_report_id"],
            ["deal_closure_report_records.deal_closure_report_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_deal_closure_report_links_report_id",
        "deal_closure_report_links",
        ["deal_closure_report_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_deal_closure_report_links_report_id", table_name="deal_closure_report_links")
    op.drop_table("deal_closure_report_links")
    op.drop_index("ix_deal_closure_report_records_report_code", table_name="deal_closure_report_records")
    op.drop_index("ix_deal_closure_report_records_set_id", table_name="deal_closure_report_records")
    op.drop_table("deal_closure_report_records")
    op.drop_index("ix_deal_closure_report_sets_closure_set_id", table_name="deal_closure_report_sets")
    op.drop_index("ix_deal_closure_report_sets_deal_id", table_name="deal_closure_report_sets")
    op.drop_table("deal_closure_report_sets")
