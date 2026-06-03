"""create integrated risk memo tables"""

from alembic import op
import sqlalchemy as sa

revision = "026_create_integrated_risk_memo"
down_revision = "025_create_contract_risk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integrated_risk_memo_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("integrated_risk_memo_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "initial_tech_risk_flag_set_id",
            sa.String(length=64),
            sa.ForeignKey("initial_tech_risk_flag_sets.risk_flag_set_id"),
            nullable=False,
        ),
        sa.Column(
            "supplier_verification_set_id",
            sa.String(length=64),
            sa.ForeignKey("supplier_verification_sets.supplier_verification_set_id"),
            nullable=False,
        ),
        sa.Column(
            "quote_comparison_set_id",
            sa.String(length=64),
            sa.ForeignKey("quote_comparison_sets.quote_comparison_set_id"),
            nullable=False,
        ),
        sa.Column("finance_memo_set_id", sa.String(length=64), sa.ForeignKey("finance_memo_sets.finance_memo_set_id"), nullable=False),
        sa.Column("contract_risk_set_id", sa.String(length=64), sa.ForeignKey("contract_risk_sets.contract_risk_set_id"), nullable=False),
        sa.Column("memo_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("integrated_risk_memo_set_id"),
    )
    op.create_index("ix_integrated_risk_memo_sets_deal_id", "integrated_risk_memo_sets", ["deal_id"])
    op.create_index(
        "ix_integrated_risk_memo_sets_finance_memo_set_id",
        "integrated_risk_memo_sets",
        ["finance_memo_set_id"],
    )

    op.create_table(
        "integrated_risk_memo_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("integrated_risk_memo_id", sa.String(length=64), nullable=False),
        sa.Column(
            "integrated_risk_memo_set_id",
            sa.String(length=64),
            sa.ForeignKey("integrated_risk_memo_sets.integrated_risk_memo_set_id"),
            nullable=False,
        ),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("structured_summary_json", sa.JSON(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("integrated_risk_memo_id"),
    )
    op.create_index(
        "ix_integrated_risk_memo_records_set_id",
        "integrated_risk_memo_records",
        ["integrated_risk_memo_set_id"],
    )

    op.create_table(
        "integrated_risk_items",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "integrated_risk_memo_id",
            sa.String(length=64),
            sa.ForeignKey("integrated_risk_memo_records.integrated_risk_memo_id"),
            nullable=False,
        ),
        sa.Column("risk_source_type", sa.Text(), nullable=False),
        sa.Column("source_object_ref", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("mitigation_hint", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_integrated_risk_items_integrated_risk_memo_id",
        "integrated_risk_items",
        ["integrated_risk_memo_id"],
    )
    op.create_index("ix_integrated_risk_items_source_type", "integrated_risk_items", ["risk_source_type"])
    op.create_index("ix_integrated_risk_items_severity", "integrated_risk_items", ["severity"])


def downgrade() -> None:
    op.drop_index("ix_integrated_risk_items_severity", table_name="integrated_risk_items")
    op.drop_index("ix_integrated_risk_items_source_type", table_name="integrated_risk_items")
    op.drop_index("ix_integrated_risk_items_integrated_risk_memo_id", table_name="integrated_risk_items")
    op.drop_table("integrated_risk_items")
    op.drop_index("ix_integrated_risk_memo_records_set_id", table_name="integrated_risk_memo_records")
    op.drop_table("integrated_risk_memo_records")
    op.drop_index("ix_integrated_risk_memo_sets_finance_memo_set_id", table_name="integrated_risk_memo_sets")
    op.drop_index("ix_integrated_risk_memo_sets_deal_id", table_name="integrated_risk_memo_sets")
    op.drop_table("integrated_risk_memo_sets")
