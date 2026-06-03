"""create bid package tables"""

from alembic import op
import sqlalchemy as sa

revision = "029_create_bid_package"
down_revision = "028_create_bid_document_collection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bid_package_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("bid_package_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "bid_document_collection_set_id",
            sa.String(length=64),
            sa.ForeignKey("bid_document_collection_sets.bid_document_collection_set_id"),
            nullable=False,
        ),
        sa.Column("package_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("bid_package_set_id"),
    )
    op.create_index("ix_bid_package_sets_deal_id", "bid_package_sets", ["deal_id"])
    op.create_index("ix_bid_package_sets_collection_set_id", "bid_package_sets", ["bid_document_collection_set_id"])

    op.create_table(
        "bid_package_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("bid_package_id", sa.String(length=64), nullable=False),
        sa.Column("bid_package_set_id", sa.String(length=64), sa.ForeignKey("bid_package_sets.bid_package_set_id"), nullable=False),
        sa.Column("package_version_no", sa.Integer(), nullable=False),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("bid_package_id"),
    )
    op.create_index("ix_bid_package_records_set_id", "bid_package_records", ["bid_package_set_id"])

    op.create_table(
        "bid_package_items",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("bid_package_id", sa.String(length=64), sa.ForeignKey("bid_package_records.bid_package_id"), nullable=False),
        sa.Column("artifact_ref", sa.String(length=64), sa.ForeignKey("document_artifacts.artifact_ref"), nullable=False),
        sa.Column("item_role", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bid_package_items_package_id", "bid_package_items", ["bid_package_id"])
    op.create_index("ix_bid_package_items_artifact_ref", "bid_package_items", ["artifact_ref"])
    op.create_index("ix_bid_package_items_item_role", "bid_package_items", ["item_role"])


def downgrade() -> None:
    op.drop_index("ix_bid_package_items_item_role", table_name="bid_package_items")
    op.drop_index("ix_bid_package_items_artifact_ref", table_name="bid_package_items")
    op.drop_index("ix_bid_package_items_package_id", table_name="bid_package_items")
    op.drop_table("bid_package_items")
    op.drop_index("ix_bid_package_records_set_id", table_name="bid_package_records")
    op.drop_table("bid_package_records")
    op.drop_index("ix_bid_package_sets_collection_set_id", table_name="bid_package_sets")
    op.drop_index("ix_bid_package_sets_deal_id", table_name="bid_package_sets")
    op.drop_table("bid_package_sets")
