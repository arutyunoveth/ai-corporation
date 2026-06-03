"""create deal registry tables"""

from alembic import op
import sqlalchemy as sa

revision = "001_create_deal_registry"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deals",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("deal_id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("customer_name", sa.Text(), nullable=True),
        sa.Column("procurement_number", sa.Text(), nullable=True),
        sa.Column("procurement_channel", sa.Text(), nullable=True),
        sa.Column("initial_source_type", sa.Text(), nullable=False),
        sa.Column("direction_type", sa.Text(), nullable=False),
        sa.Column("domain_type", sa.Text(), nullable=False),
        sa.Column("current_status", sa.Text(), nullable=False),
        sa.Column("priority_bucket", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("deal_id"),
    )
    op.create_index("ix_deals_current_status", "deals", ["current_status"])
    op.create_index("ix_deals_created_at", "deals", ["created_at"])
    op.create_index("ix_deals_procurement_number", "deals", ["procurement_number"])

    op.create_table(
        "deal_external_refs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("ref_type", sa.Text(), nullable=False),
        sa.Column("ref_value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_deal_external_refs_deal_id", "deal_external_refs", ["deal_id"])
    op.create_index("ix_deal_external_refs_ref_type", "deal_external_refs", ["ref_type"])

    op.create_table(
        "deal_tags",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("tag_code", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_deal_tags_deal_id", "deal_tags", ["deal_id"])
    op.create_index("ix_deal_tags_tag_code", "deal_tags", ["tag_code"])


def downgrade() -> None:
    op.drop_index("ix_deal_tags_tag_code", table_name="deal_tags")
    op.drop_index("ix_deal_tags_deal_id", table_name="deal_tags")
    op.drop_table("deal_tags")
    op.drop_index("ix_deal_external_refs_ref_type", table_name="deal_external_refs")
    op.drop_index("ix_deal_external_refs_deal_id", table_name="deal_external_refs")
    op.drop_table("deal_external_refs")
    op.drop_index("ix_deals_procurement_number", table_name="deals")
    op.drop_index("ix_deals_created_at", table_name="deals")
    op.drop_index("ix_deals_current_status", table_name="deals")
    op.drop_table("deals")

