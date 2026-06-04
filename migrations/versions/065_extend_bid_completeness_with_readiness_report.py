"""extend bid completeness with readiness reports"""

from alembic import op
import sqlalchemy as sa

revision = "065_extend_bid_completeness_with_readiness_report"
down_revision = "064_create_requirement_extraction"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bid_readiness_reports",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("bid_readiness_report_id", sa.String(length=64), nullable=False),
        sa.Column(
            "bid_completeness_set_id",
            sa.String(length=64),
            sa.ForeignKey("bid_completeness_sets.bid_completeness_set_id"),
            nullable=False,
        ),
        sa.Column("readiness_summary", sa.Text(), nullable=False),
        sa.Column("blocking_issue_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("bid_readiness_report_id"),
    )
    op.create_index("ix_bid_readiness_reports_set_id", "bid_readiness_reports", ["bid_completeness_set_id"])


def downgrade() -> None:
    op.drop_index("ix_bid_readiness_reports_set_id", table_name="bid_readiness_reports")
    op.drop_table("bid_readiness_reports")
