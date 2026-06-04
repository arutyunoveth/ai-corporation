"""create purchase order tables

Revision ID: 071_create_purchase_orders
Revises: 070_create_execution_plans
Create Date: 2026-06-04 09:40:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "071_create_purchase_orders"
down_revision: str | Sequence[str] | None = "070_create_execution_plans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "purchase_order_sets",
        sa.Column("purchase_order_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), nullable=False),
        sa.Column("supplier_id", sa.String(length=64), nullable=False),
        sa.Column("po_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.deal_id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["supplier_profiles.supplier_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("purchase_order_set_id"),
    )
    op.create_index("ix_purchase_order_sets_deal_id", "purchase_order_sets", ["deal_id"])
    op.create_index("ix_purchase_order_sets_supplier_id", "purchase_order_sets", ["supplier_id"])

    op.create_table(
        "purchase_order_records",
        sa.Column("purchase_order_id", sa.String(length=64), nullable=False),
        sa.Column("purchase_order_set_id", sa.String(length=64), nullable=False),
        sa.Column("po_number", sa.String(length=64), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["purchase_order_set_id"], ["purchase_order_sets.purchase_order_set_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("purchase_order_id"),
    )
    op.create_index("ix_purchase_order_records_set_id", "purchase_order_records", ["purchase_order_set_id"])
    op.create_index("ix_purchase_order_records_po_number", "purchase_order_records", ["po_number"])

    op.create_table(
        "purchase_order_items",
        sa.Column("purchase_order_id", sa.String(length=64), nullable=False),
        sa.Column("item_code", sa.String(length=64), nullable=False),
        sa.Column("item_description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_order_records.purchase_order_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_order_items_purchase_order_id", "purchase_order_items", ["purchase_order_id"])
    op.create_index("ix_purchase_order_items_item_code", "purchase_order_items", ["item_code"])

    op.create_table(
        "purchase_order_links",
        sa.Column("purchase_order_id", sa.String(length=64), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_order_records.purchase_order_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_order_links_purchase_order_id", "purchase_order_links", ["purchase_order_id"])


def downgrade() -> None:
    op.drop_index("ix_purchase_order_links_purchase_order_id", table_name="purchase_order_links")
    op.drop_table("purchase_order_links")
    op.drop_index("ix_purchase_order_items_item_code", table_name="purchase_order_items")
    op.drop_index("ix_purchase_order_items_purchase_order_id", table_name="purchase_order_items")
    op.drop_table("purchase_order_items")
    op.drop_index("ix_purchase_order_records_po_number", table_name="purchase_order_records")
    op.drop_index("ix_purchase_order_records_set_id", table_name="purchase_order_records")
    op.drop_table("purchase_order_records")
    op.drop_index("ix_purchase_order_sets_supplier_id", table_name="purchase_order_sets")
    op.drop_index("ix_purchase_order_sets_deal_id", table_name="purchase_order_sets")
    op.drop_table("purchase_order_sets")
