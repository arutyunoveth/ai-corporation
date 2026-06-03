"""create quote comparison tables"""

from alembic import op
import sqlalchemy as sa

revision = "020_create_quote_comparison"
down_revision = "019_create_supplier_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quote_comparison_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("quote_comparison_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("quote_set_id", sa.String(length=64), sa.ForeignKey("quote_sets.quote_set_id"), nullable=False),
        sa.Column(
            "supplier_verification_set_id",
            sa.String(length=64),
            sa.ForeignKey("supplier_verification_sets.supplier_verification_set_id"),
            nullable=False,
        ),
        sa.Column("comparison_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("quote_comparison_set_id"),
    )
    op.create_index("ix_quote_comparison_sets_deal_id", "quote_comparison_sets", ["deal_id"])
    op.create_index("ix_quote_comparison_sets_quote_set_id", "quote_comparison_sets", ["quote_set_id"])

    op.create_table(
        "quote_comparison_rows",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "quote_comparison_set_id",
            sa.String(length=64),
            sa.ForeignKey("quote_comparison_sets.quote_comparison_set_id"),
            nullable=False,
        ),
        sa.Column("quote_id", sa.String(length=64), sa.ForeignKey("quote_records.quote_id"), nullable=False),
        sa.Column("supplier_id", sa.String(length=64), sa.ForeignKey("supplier_profiles.supplier_id"), nullable=False),
        sa.Column("price_score", sa.Float(), nullable=False),
        sa.Column("delivery_score", sa.Float(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("rank_order", sa.Integer(), nullable=False),
        sa.Column("comparison_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_quote_comparison_rows_set_id", "quote_comparison_rows", ["quote_comparison_set_id"])
    op.create_index("ix_quote_comparison_rows_quote_id", "quote_comparison_rows", ["quote_id"])
    op.create_index("ix_quote_comparison_rows_supplier_id", "quote_comparison_rows", ["supplier_id"])

    op.create_table(
        "quote_comparison_recommendations",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "quote_comparison_set_id",
            sa.String(length=64),
            sa.ForeignKey("quote_comparison_sets.quote_comparison_set_id"),
            nullable=False,
        ),
        sa.Column("recommended_quote_id", sa.String(length=64), sa.ForeignKey("quote_records.quote_id"), nullable=False),
        sa.Column(
            "recommended_supplier_id",
            sa.String(length=64),
            sa.ForeignKey("supplier_profiles.supplier_id"),
            nullable=False,
        ),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_quote_comparison_recommendations_set_id",
        "quote_comparison_recommendations",
        ["quote_comparison_set_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_quote_comparison_recommendations_set_id",
        table_name="quote_comparison_recommendations",
    )
    op.drop_table("quote_comparison_recommendations")
    op.drop_index("ix_quote_comparison_rows_supplier_id", table_name="quote_comparison_rows")
    op.drop_index("ix_quote_comparison_rows_quote_id", table_name="quote_comparison_rows")
    op.drop_index("ix_quote_comparison_rows_set_id", table_name="quote_comparison_rows")
    op.drop_table("quote_comparison_rows")
    op.drop_index("ix_quote_comparison_sets_quote_set_id", table_name="quote_comparison_sets")
    op.drop_index("ix_quote_comparison_sets_deal_id", table_name="quote_comparison_sets")
    op.drop_table("quote_comparison_sets")
