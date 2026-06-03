"""create cost model tables"""

from alembic import op
import sqlalchemy as sa

revision = "021_create_cost_model"
down_revision = "020_create_quote_comparison"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cost_model_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("cost_model_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "quote_comparison_set_id",
            sa.String(length=64),
            sa.ForeignKey("quote_comparison_sets.quote_comparison_set_id"),
            nullable=False,
        ),
        sa.Column("cost_model_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("cost_model_set_id"),
    )
    op.create_index("ix_cost_model_sets_deal_id", "cost_model_sets", ["deal_id"])
    op.create_index(
        "ix_cost_model_sets_quote_comparison_set_id",
        "cost_model_sets",
        ["quote_comparison_set_id"],
    )

    op.create_table(
        "cost_model_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("cost_model_id", sa.String(length=64), nullable=False),
        sa.Column("cost_model_set_id", sa.String(length=64), sa.ForeignKey("cost_model_sets.cost_model_set_id"), nullable=False),
        sa.Column("base_quote_total", sa.Float(), nullable=False),
        sa.Column("logistics_cost", sa.Float(), nullable=False),
        sa.Column("buffer_cost", sa.Float(), nullable=False),
        sa.Column("overhead_cost", sa.Float(), nullable=False),
        sa.Column("total_cost", sa.Float(), nullable=False),
        sa.Column("min_viable_bid", sa.Float(), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("cost_model_id"),
    )
    op.create_index("ix_cost_model_records_set_id", "cost_model_records", ["cost_model_set_id"])

    op.create_table(
        "cost_model_lines",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("cost_model_id", sa.String(length=64), sa.ForeignKey("cost_model_records.cost_model_id"), nullable=False),
        sa.Column("line_code", sa.String(length=64), nullable=False),
        sa.Column("line_type", sa.Text(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cost_model_lines_cost_model_id", "cost_model_lines", ["cost_model_id"])
    op.create_index("ix_cost_model_lines_line_type", "cost_model_lines", ["line_type"])


def downgrade() -> None:
    op.drop_index("ix_cost_model_lines_line_type", table_name="cost_model_lines")
    op.drop_index("ix_cost_model_lines_cost_model_id", table_name="cost_model_lines")
    op.drop_table("cost_model_lines")
    op.drop_index("ix_cost_model_records_set_id", table_name="cost_model_records")
    op.drop_table("cost_model_records")
    op.drop_index("ix_cost_model_sets_quote_comparison_set_id", table_name="cost_model_sets")
    op.drop_index("ix_cost_model_sets_deal_id", table_name="cost_model_sets")
    op.drop_table("cost_model_sets")
