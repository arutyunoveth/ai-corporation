"""create cash gap tables"""

from alembic import op
import sqlalchemy as sa

revision = "022_create_cash_gap"
down_revision = "021_create_cost_model"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cash_gap_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("cash_gap_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("cost_model_set_id", sa.String(length=64), sa.ForeignKey("cost_model_sets.cost_model_set_id"), nullable=False),
        sa.Column("cash_gap_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("cash_gap_set_id"),
    )
    op.create_index("ix_cash_gap_sets_deal_id", "cash_gap_sets", ["deal_id"])
    op.create_index("ix_cash_gap_sets_cost_model_set_id", "cash_gap_sets", ["cost_model_set_id"])

    op.create_table(
        "cash_gap_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("cash_gap_id", sa.String(length=64), nullable=False),
        sa.Column("cash_gap_set_id", sa.String(length=64), sa.ForeignKey("cash_gap_sets.cash_gap_set_id"), nullable=False),
        sa.Column("peak_gap_amount", sa.Float(), nullable=False),
        sa.Column("gap_duration_days", sa.Integer(), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("cash_gap_id"),
    )
    op.create_index("ix_cash_gap_records_set_id", "cash_gap_records", ["cash_gap_set_id"])

    op.create_table(
        "cash_gap_scenarios",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("cash_gap_id", sa.String(length=64), sa.ForeignKey("cash_gap_records.cash_gap_id"), nullable=False),
        sa.Column("scenario_code", sa.String(length=64), nullable=False),
        sa.Column("scenario_name", sa.Text(), nullable=False),
        sa.Column("peak_gap_amount", sa.Float(), nullable=False),
        sa.Column("gap_duration_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cash_gap_scenarios_cash_gap_id", "cash_gap_scenarios", ["cash_gap_id"])
    op.create_index("ix_cash_gap_scenarios_scenario_code", "cash_gap_scenarios", ["scenario_code"])


def downgrade() -> None:
    op.drop_index("ix_cash_gap_scenarios_scenario_code", table_name="cash_gap_scenarios")
    op.drop_index("ix_cash_gap_scenarios_cash_gap_id", table_name="cash_gap_scenarios")
    op.drop_table("cash_gap_scenarios")
    op.drop_index("ix_cash_gap_records_set_id", table_name="cash_gap_records")
    op.drop_table("cash_gap_records")
    op.drop_index("ix_cash_gap_sets_cost_model_set_id", table_name="cash_gap_sets")
    op.drop_index("ix_cash_gap_sets_deal_id", table_name="cash_gap_sets")
    op.drop_table("cash_gap_sets")
