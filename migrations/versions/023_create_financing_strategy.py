"""create financing strategy tables"""

from alembic import op
import sqlalchemy as sa

revision = "023_create_financing_strategy"
down_revision = "022_create_cash_gap"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "financing_strategy_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("financing_strategy_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("cash_gap_set_id", sa.String(length=64), sa.ForeignKey("cash_gap_sets.cash_gap_set_id"), nullable=False),
        sa.Column("strategy_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("financing_strategy_set_id"),
    )
    op.create_index("ix_financing_strategy_sets_deal_id", "financing_strategy_sets", ["deal_id"])
    op.create_index("ix_financing_strategy_sets_cash_gap_set_id", "financing_strategy_sets", ["cash_gap_set_id"])

    op.create_table(
        "financing_strategy_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("financing_strategy_id", sa.String(length=64), nullable=False),
        sa.Column(
            "financing_strategy_set_id",
            sa.String(length=64),
            sa.ForeignKey("financing_strategy_sets.financing_strategy_set_id"),
            nullable=False,
        ),
        sa.Column("recommended_option_code", sa.String(length=64), nullable=False),
        sa.Column("feasible", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("financing_strategy_id"),
    )
    op.create_index("ix_financing_strategy_records_set_id", "financing_strategy_records", ["financing_strategy_set_id"])

    op.create_table(
        "financing_strategy_options",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "financing_strategy_id",
            sa.String(length=64),
            sa.ForeignKey("financing_strategy_records.financing_strategy_id"),
            nullable=False,
        ),
        sa.Column("option_code", sa.String(length=64), nullable=False),
        sa.Column("option_name", sa.Text(), nullable=False),
        sa.Column("funding_amount", sa.Float(), nullable=False),
        sa.Column("funding_cost", sa.Float(), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("feasibility_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_financing_strategy_options_financing_strategy_id",
        "financing_strategy_options",
        ["financing_strategy_id"],
    )
    op.create_index("ix_financing_strategy_options_option_code", "financing_strategy_options", ["option_code"])


def downgrade() -> None:
    op.drop_index("ix_financing_strategy_options_option_code", table_name="financing_strategy_options")
    op.drop_index(
        "ix_financing_strategy_options_financing_strategy_id",
        table_name="financing_strategy_options",
    )
    op.drop_table("financing_strategy_options")
    op.drop_index("ix_financing_strategy_records_set_id", table_name="financing_strategy_records")
    op.drop_table("financing_strategy_records")
    op.drop_index("ix_financing_strategy_sets_cash_gap_set_id", table_name="financing_strategy_sets")
    op.drop_index("ix_financing_strategy_sets_deal_id", table_name="financing_strategy_sets")
    op.drop_table("financing_strategy_sets")
