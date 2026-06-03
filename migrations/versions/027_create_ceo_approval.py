"""create ceo approval tables"""

from alembic import op
import sqlalchemy as sa

revision = "027_create_ceo_approval"
down_revision = "026_create_integrated_risk_memo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ceo_approval_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("ceo_approval_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("finance_memo_set_id", sa.String(length=64), sa.ForeignKey("finance_memo_sets.finance_memo_set_id"), nullable=False),
        sa.Column(
            "integrated_risk_memo_set_id",
            sa.String(length=64),
            sa.ForeignKey("integrated_risk_memo_sets.integrated_risk_memo_set_id"),
            nullable=False,
        ),
        sa.Column("approval_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("ceo_approval_set_id"),
    )
    op.create_index("ix_ceo_approval_sets_deal_id", "ceo_approval_sets", ["deal_id"])
    op.create_index("ix_ceo_approval_sets_finance_memo_set_id", "ceo_approval_sets", ["finance_memo_set_id"])

    op.create_table(
        "ceo_approval_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("ceo_approval_id", sa.String(length=64), nullable=False),
        sa.Column("ceo_approval_set_id", sa.String(length=64), sa.ForeignKey("ceo_approval_sets.ceo_approval_set_id"), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("decided_by_ref", sa.Text(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("ceo_approval_id"),
    )
    op.create_index("ix_ceo_approval_records_set_id", "ceo_approval_records", ["ceo_approval_set_id"])
    op.create_index("ix_ceo_approval_records_decision", "ceo_approval_records", ["decision"])

    op.create_table(
        "ceo_approval_conditions",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("ceo_approval_id", sa.String(length=64), sa.ForeignKey("ceo_approval_records.ceo_approval_id"), nullable=False),
        sa.Column("condition_code", sa.String(length=64), nullable=False),
        sa.Column("condition_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ceo_approval_conditions_ceo_approval_id", "ceo_approval_conditions", ["ceo_approval_id"])
    op.create_index("ix_ceo_approval_conditions_condition_code", "ceo_approval_conditions", ["condition_code"])


def downgrade() -> None:
    op.drop_index("ix_ceo_approval_conditions_condition_code", table_name="ceo_approval_conditions")
    op.drop_index("ix_ceo_approval_conditions_ceo_approval_id", table_name="ceo_approval_conditions")
    op.drop_table("ceo_approval_conditions")
    op.drop_index("ix_ceo_approval_records_decision", table_name="ceo_approval_records")
    op.drop_index("ix_ceo_approval_records_set_id", table_name="ceo_approval_records")
    op.drop_table("ceo_approval_records")
    op.drop_index("ix_ceo_approval_sets_finance_memo_set_id", table_name="ceo_approval_sets")
    op.drop_index("ix_ceo_approval_sets_deal_id", table_name="ceo_approval_sets")
    op.drop_table("ceo_approval_sets")
