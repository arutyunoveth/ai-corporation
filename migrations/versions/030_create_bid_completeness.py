"""create bid completeness tables"""

from alembic import op
import sqlalchemy as sa

revision = "030_create_bid_completeness"
down_revision = "029_create_bid_package"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bid_completeness_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("bid_completeness_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("bid_package_set_id", sa.String(length=64), sa.ForeignKey("bid_package_sets.bid_package_set_id"), nullable=False),
        sa.Column("completeness_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("bid_completeness_set_id"),
    )
    op.create_index("ix_bid_completeness_sets_deal_id", "bid_completeness_sets", ["deal_id"])
    op.create_index("ix_bid_completeness_sets_package_set_id", "bid_completeness_sets", ["bid_package_set_id"])

    op.create_table(
        "bid_completeness_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("bid_completeness_id", sa.String(length=64), nullable=False),
        sa.Column("bid_completeness_set_id", sa.String(length=64), sa.ForeignKey("bid_completeness_sets.bid_completeness_set_id"), nullable=False),
        sa.Column("mandatory_total", sa.Integer(), nullable=False),
        sa.Column("mandatory_present", sa.Integer(), nullable=False),
        sa.Column("optional_present", sa.Integer(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("bid_completeness_id"),
    )
    op.create_index("ix_bid_completeness_records_set_id", "bid_completeness_records", ["bid_completeness_set_id"])

    op.create_table(
        "bid_completeness_flags",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("bid_completeness_id", sa.String(length=64), sa.ForeignKey("bid_completeness_records.bid_completeness_id"), nullable=False),
        sa.Column("flag_code", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bid_completeness_flags_completeness_id", "bid_completeness_flags", ["bid_completeness_id"])
    op.create_index("ix_bid_completeness_flags_severity", "bid_completeness_flags", ["severity"])


def downgrade() -> None:
    op.drop_index("ix_bid_completeness_flags_severity", table_name="bid_completeness_flags")
    op.drop_index("ix_bid_completeness_flags_completeness_id", table_name="bid_completeness_flags")
    op.drop_table("bid_completeness_flags")
    op.drop_index("ix_bid_completeness_records_set_id", table_name="bid_completeness_records")
    op.drop_table("bid_completeness_records")
    op.drop_index("ix_bid_completeness_sets_package_set_id", table_name="bid_completeness_sets")
    op.drop_index("ix_bid_completeness_sets_deal_id", table_name="bid_completeness_sets")
    op.drop_table("bid_completeness_sets")
