"""create finance memo tables"""

from alembic import op
import sqlalchemy as sa

revision = "024_create_finance_memo"
down_revision = "023_create_financing_strategy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "finance_memo_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("finance_memo_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("cost_model_set_id", sa.String(length=64), sa.ForeignKey("cost_model_sets.cost_model_set_id"), nullable=False),
        sa.Column("cash_gap_set_id", sa.String(length=64), sa.ForeignKey("cash_gap_sets.cash_gap_set_id"), nullable=False),
        sa.Column(
            "financing_strategy_set_id",
            sa.String(length=64),
            sa.ForeignKey("financing_strategy_sets.financing_strategy_set_id"),
            nullable=False,
        ),
        sa.Column("memo_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("finance_memo_set_id"),
    )
    op.create_index("ix_finance_memo_sets_deal_id", "finance_memo_sets", ["deal_id"])
    op.create_index("ix_finance_memo_sets_cost_model_set_id", "finance_memo_sets", ["cost_model_set_id"])

    op.create_table(
        "finance_memo_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("finance_memo_id", sa.String(length=64), nullable=False),
        sa.Column("finance_memo_set_id", sa.String(length=64), sa.ForeignKey("finance_memo_sets.finance_memo_set_id"), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("structured_summary_json", sa.JSON(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("finance_memo_id"),
    )
    op.create_index("ix_finance_memo_records_set_id", "finance_memo_records", ["finance_memo_set_id"])

    op.create_table(
        "finance_memo_flags",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("finance_memo_id", sa.String(length=64), sa.ForeignKey("finance_memo_records.finance_memo_id"), nullable=False),
        sa.Column("flag_code", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_finance_memo_flags_finance_memo_id", "finance_memo_flags", ["finance_memo_id"])
    op.create_index("ix_finance_memo_flags_severity", "finance_memo_flags", ["severity"])


def downgrade() -> None:
    op.drop_index("ix_finance_memo_flags_severity", table_name="finance_memo_flags")
    op.drop_index("ix_finance_memo_flags_finance_memo_id", table_name="finance_memo_flags")
    op.drop_table("finance_memo_flags")
    op.drop_index("ix_finance_memo_records_set_id", table_name="finance_memo_records")
    op.drop_table("finance_memo_records")
    op.drop_index("ix_finance_memo_sets_cost_model_set_id", table_name="finance_memo_sets")
    op.drop_index("ix_finance_memo_sets_deal_id", table_name="finance_memo_sets")
    op.drop_table("finance_memo_sets")
