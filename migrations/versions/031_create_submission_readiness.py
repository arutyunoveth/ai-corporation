"""create submission readiness tables"""

from alembic import op
import sqlalchemy as sa

revision = "031_create_submission_readiness"
down_revision = "030_create_bid_completeness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "submission_readiness_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("submission_readiness_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("bid_completeness_set_id", sa.String(length=64), sa.ForeignKey("bid_completeness_sets.bid_completeness_set_id"), nullable=False),
        sa.Column("ceo_approval_set_id", sa.String(length=64), sa.ForeignKey("ceo_approval_sets.ceo_approval_set_id"), nullable=False),
        sa.Column("finance_memo_set_id", sa.String(length=64), sa.ForeignKey("finance_memo_sets.finance_memo_set_id"), nullable=False),
        sa.Column(
            "integrated_risk_memo_set_id",
            sa.String(length=64),
            sa.ForeignKey("integrated_risk_memo_sets.integrated_risk_memo_set_id"),
            nullable=False,
        ),
        sa.Column("readiness_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("submission_readiness_set_id"),
    )
    op.create_index("ix_submission_readiness_sets_deal_id", "submission_readiness_sets", ["deal_id"])
    op.create_index(
        "ix_submission_readiness_sets_completeness_set_id",
        "submission_readiness_sets",
        ["bid_completeness_set_id"],
    )

    op.create_table(
        "submission_readiness_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("submission_readiness_id", sa.String(length=64), nullable=False),
        sa.Column(
            "submission_readiness_set_id",
            sa.String(length=64),
            sa.ForeignKey("submission_readiness_sets.submission_readiness_set_id"),
            nullable=False,
        ),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("submission_readiness_id"),
    )
    op.create_index("ix_submission_readiness_records_set_id", "submission_readiness_records", ["submission_readiness_set_id"])

    op.create_table(
        "submission_readiness_flags",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "submission_readiness_id",
            sa.String(length=64),
            sa.ForeignKey("submission_readiness_records.submission_readiness_id"),
            nullable=False,
        ),
        sa.Column("flag_code", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_submission_readiness_flags_submission_readiness_id", "submission_readiness_flags", ["submission_readiness_id"])
    op.create_index("ix_submission_readiness_flags_severity", "submission_readiness_flags", ["severity"])


def downgrade() -> None:
    op.drop_index("ix_submission_readiness_flags_severity", table_name="submission_readiness_flags")
    op.drop_index("ix_submission_readiness_flags_submission_readiness_id", table_name="submission_readiness_flags")
    op.drop_table("submission_readiness_flags")
    op.drop_index("ix_submission_readiness_records_set_id", table_name="submission_readiness_records")
    op.drop_table("submission_readiness_records")
    op.drop_index("ix_submission_readiness_sets_completeness_set_id", table_name="submission_readiness_sets")
    op.drop_index("ix_submission_readiness_sets_deal_id", table_name="submission_readiness_sets")
    op.drop_table("submission_readiness_sets")
