"""create claim trigger tables

Revision ID: 078_create_claim_triggers
Revises: 077_create_payment_tracking
Create Date: 2026-06-04 12:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "078_create_claim_triggers"
down_revision: str | Sequence[str] | None = "077_create_payment_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "claim_trigger_sets",
        sa.Column("claim_trigger_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), nullable=False),
        sa.Column("trigger_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.deal_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_trigger_set_id"),
    )
    op.create_index("ix_claim_trigger_sets_deal_id", "claim_trigger_sets", ["deal_id"])

    op.create_table(
        "claim_trigger_records",
        sa.Column("claim_trigger_id", sa.String(length=64), nullable=False),
        sa.Column("claim_trigger_set_id", sa.String(length=64), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("trigger_reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["claim_trigger_set_id"], ["claim_trigger_sets.claim_trigger_set_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_trigger_id"),
    )
    op.create_index("ix_claim_trigger_records_set_id", "claim_trigger_records", ["claim_trigger_set_id"])

    op.create_table(
        "claim_trigger_flags",
        sa.Column("claim_trigger_id", sa.String(length=64), nullable=False),
        sa.Column("flag_code", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["claim_trigger_id"], ["claim_trigger_records.claim_trigger_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_claim_trigger_flags_trigger_id", "claim_trigger_flags", ["claim_trigger_id"])
    op.create_index("ix_claim_trigger_flags_flag_code", "claim_trigger_flags", ["flag_code"])

    op.create_table(
        "claim_trigger_links",
        sa.Column("claim_trigger_id", sa.String(length=64), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["claim_trigger_id"], ["claim_trigger_records.claim_trigger_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_claim_trigger_links_trigger_id", "claim_trigger_links", ["claim_trigger_id"])


def downgrade() -> None:
    op.drop_index("ix_claim_trigger_links_trigger_id", table_name="claim_trigger_links")
    op.drop_table("claim_trigger_links")
    op.drop_index("ix_claim_trigger_flags_flag_code", table_name="claim_trigger_flags")
    op.drop_index("ix_claim_trigger_flags_trigger_id", table_name="claim_trigger_flags")
    op.drop_table("claim_trigger_flags")
    op.drop_index("ix_claim_trigger_records_set_id", table_name="claim_trigger_records")
    op.drop_table("claim_trigger_records")
    op.drop_index("ix_claim_trigger_sets_deal_id", table_name="claim_trigger_sets")
    op.drop_table("claim_trigger_sets")
