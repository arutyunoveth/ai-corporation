"""create acceptance control tables

Revision ID: 075_create_acceptance_control
Revises: 074_create_incident_register
Create Date: 2026-06-04 11:30:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "075_create_acceptance_control"
down_revision: str | Sequence[str] | None = "074_create_incident_register"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "acceptance_control_sets",
        sa.Column("acceptance_control_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), nullable=False),
        sa.Column("acceptance_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.deal_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("acceptance_control_set_id"),
    )
    op.create_index("ix_acceptance_control_sets_deal_id", "acceptance_control_sets", ["deal_id"])

    op.create_table(
        "acceptance_control_records",
        sa.Column("acceptance_control_id", sa.String(length=64), nullable=False),
        sa.Column("acceptance_control_set_id", sa.String(length=64), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("resolution_state", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["acceptance_control_set_id"], ["acceptance_control_sets.acceptance_control_set_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("acceptance_control_id"),
    )
    op.create_index("ix_acceptance_control_records_set_id", "acceptance_control_records", ["acceptance_control_set_id"])

    op.create_table(
        "acceptance_remarks",
        sa.Column("acceptance_control_id", sa.String(length=64), nullable=False),
        sa.Column("remark_code", sa.String(length=64), nullable=False),
        sa.Column("remark_text", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["acceptance_control_id"], ["acceptance_control_records.acceptance_control_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_acceptance_remarks_control_id", "acceptance_remarks", ["acceptance_control_id"])
    op.create_index("ix_acceptance_remarks_remark_code", "acceptance_remarks", ["remark_code"])

    op.create_table(
        "acceptance_resolution_items",
        sa.Column("acceptance_control_id", sa.String(length=64), nullable=False),
        sa.Column("item_code", sa.String(length=64), nullable=False),
        sa.Column("resolution_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["acceptance_control_id"], ["acceptance_control_records.acceptance_control_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_acceptance_resolution_items_control_id", "acceptance_resolution_items", ["acceptance_control_id"])
    op.create_index("ix_acceptance_resolution_items_item_code", "acceptance_resolution_items", ["item_code"])


def downgrade() -> None:
    op.drop_index("ix_acceptance_resolution_items_item_code", table_name="acceptance_resolution_items")
    op.drop_index("ix_acceptance_resolution_items_control_id", table_name="acceptance_resolution_items")
    op.drop_table("acceptance_resolution_items")
    op.drop_index("ix_acceptance_remarks_remark_code", table_name="acceptance_remarks")
    op.drop_index("ix_acceptance_remarks_control_id", table_name="acceptance_remarks")
    op.drop_table("acceptance_remarks")
    op.drop_index("ix_acceptance_control_records_set_id", table_name="acceptance_control_records")
    op.drop_table("acceptance_control_records")
    op.drop_index("ix_acceptance_control_sets_deal_id", table_name="acceptance_control_sets")
    op.drop_table("acceptance_control_sets")
