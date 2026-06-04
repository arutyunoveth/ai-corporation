"""create closing docs tables

Revision ID: 076_create_closing_docs
Revises: 075_create_acceptance_control
Create Date: 2026-06-04 11:40:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "076_create_closing_docs"
down_revision: str | Sequence[str] | None = "075_create_acceptance_control"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "closing_docs_sets",
        sa.Column("closing_docs_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), nullable=False),
        sa.Column("docs_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.deal_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("closing_docs_set_id"),
    )
    op.create_index("ix_closing_docs_sets_deal_id", "closing_docs_sets", ["deal_id"])

    op.create_table(
        "closing_docs_records",
        sa.Column("closing_docs_id", sa.String(length=64), nullable=False),
        sa.Column("closing_docs_set_id", sa.String(length=64), nullable=False),
        sa.Column("docs_manifest_json", sa.Text(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["closing_docs_set_id"], ["closing_docs_sets.closing_docs_set_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("closing_docs_id"),
    )
    op.create_index("ix_closing_docs_records_set_id", "closing_docs_records", ["closing_docs_set_id"])

    op.create_table(
        "closing_docs_items",
        sa.Column("closing_docs_id", sa.String(length=64), nullable=False),
        sa.Column("item_code", sa.String(length=64), nullable=False),
        sa.Column("artifact_ref", sa.String(length=128), nullable=True),
        sa.Column("item_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["closing_docs_id"], ["closing_docs_records.closing_docs_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_closing_docs_items_docs_id", "closing_docs_items", ["closing_docs_id"])
    op.create_index("ix_closing_docs_items_item_code", "closing_docs_items", ["item_code"])

    op.create_table(
        "closing_docs_flags",
        sa.Column("closing_docs_id", sa.String(length=64), nullable=False),
        sa.Column("flag_code", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["closing_docs_id"], ["closing_docs_records.closing_docs_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_closing_docs_flags_docs_id", "closing_docs_flags", ["closing_docs_id"])
    op.create_index("ix_closing_docs_flags_flag_code", "closing_docs_flags", ["flag_code"])


def downgrade() -> None:
    op.drop_index("ix_closing_docs_flags_flag_code", table_name="closing_docs_flags")
    op.drop_index("ix_closing_docs_flags_docs_id", table_name="closing_docs_flags")
    op.drop_table("closing_docs_flags")
    op.drop_index("ix_closing_docs_items_item_code", table_name="closing_docs_items")
    op.drop_index("ix_closing_docs_items_docs_id", table_name="closing_docs_items")
    op.drop_table("closing_docs_items")
    op.drop_index("ix_closing_docs_records_set_id", table_name="closing_docs_records")
    op.drop_table("closing_docs_records")
    op.drop_index("ix_closing_docs_sets_deal_id", table_name="closing_docs_sets")
    op.drop_table("closing_docs_sets")
