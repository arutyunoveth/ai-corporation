"""create launch visibility tables

Revision ID: 083_create_launch_visibility
Revises: 082_create_knowledge_assets
Create Date: 2026-06-05 10:45:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "083_create_launch_visibility"
down_revision: str | Sequence[str] | None = "082_create_knowledge_assets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "launch_visibility_sets",
        sa.Column("launch_visibility_set_id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_ref", sa.String(length=128), nullable=False),
        sa.Column("visibility_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("launch_visibility_set_id"),
    )
    op.create_index("ix_launch_visibility_sets_scope_type", "launch_visibility_sets", ["scope_type"])
    op.create_index("ix_launch_visibility_sets_scope_ref", "launch_visibility_sets", ["scope_ref"])

    op.create_table(
        "launch_visibility_records",
        sa.Column("launch_visibility_id", sa.String(length=64), nullable=False),
        sa.Column("launch_visibility_set_id", sa.String(length=64), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("active_deal_count", sa.Integer(), nullable=False),
        sa.Column("blocked_deal_count", sa.Integer(), nullable=False),
        sa.Column("attention_count", sa.Integer(), nullable=False),
        sa.Column("red_flag_count", sa.Integer(), nullable=False),
        sa.Column("manual_review_count", sa.Integer(), nullable=False),
        sa.Column("overdue_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["launch_visibility_set_id"],
            ["launch_visibility_sets.launch_visibility_set_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("launch_visibility_id"),
    )
    op.create_index("ix_launch_visibility_records_set_id", "launch_visibility_records", ["launch_visibility_set_id"])

    op.create_table(
        "launch_visibility_items",
        sa.Column("launch_visibility_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), nullable=True),
        sa.Column("item_code", sa.String(length=64), nullable=False),
        sa.Column("item_type", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("source_module_id", sa.String(length=64), nullable=True),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("detail_text", sa.Text(), nullable=False),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.deal_id"]),
        sa.ForeignKeyConstraint(
            ["launch_visibility_id"],
            ["launch_visibility_records.launch_visibility_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_launch_visibility_items_visibility_id", "launch_visibility_items", ["launch_visibility_id"])
    op.create_index("ix_launch_visibility_items_deal_id", "launch_visibility_items", ["deal_id"])
    op.create_index("ix_launch_visibility_items_item_type", "launch_visibility_items", ["item_type"])
    op.create_index("ix_launch_visibility_items_severity", "launch_visibility_items", ["severity"])


def downgrade() -> None:
    op.drop_index("ix_launch_visibility_items_severity", table_name="launch_visibility_items")
    op.drop_index("ix_launch_visibility_items_item_type", table_name="launch_visibility_items")
    op.drop_index("ix_launch_visibility_items_deal_id", table_name="launch_visibility_items")
    op.drop_index("ix_launch_visibility_items_visibility_id", table_name="launch_visibility_items")
    op.drop_table("launch_visibility_items")
    op.drop_index("ix_launch_visibility_records_set_id", table_name="launch_visibility_records")
    op.drop_table("launch_visibility_records")
    op.drop_index("ix_launch_visibility_sets_scope_ref", table_name="launch_visibility_sets")
    op.drop_index("ix_launch_visibility_sets_scope_type", table_name="launch_visibility_sets")
    op.drop_table("launch_visibility_sets")
