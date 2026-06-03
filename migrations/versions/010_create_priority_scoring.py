"""create priority scoring tables"""

from alembic import op
import sqlalchemy as sa

revision = "010_create_priority_scoring"
down_revision = "009_create_tender_screening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "priority_score_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("priority_score_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("intake_id", sa.String(length=64), sa.ForeignKey("tender_intake_records.intake_id"), nullable=False),
        sa.Column("document_set_id", sa.String(length=64), sa.ForeignKey("document_sets.document_set_id"), nullable=False),
        sa.Column("tender_summary_id", sa.String(length=64), sa.ForeignKey("tender_summaries.tender_summary_id"), nullable=False),
        sa.Column("screening_id", sa.String(length=64), sa.ForeignKey("tender_screening_records.screening_id"), nullable=False),
        sa.Column("priority_score", sa.Float(), nullable=False),
        sa.Column("priority_bucket", sa.Text(), nullable=False),
        sa.Column("rationale_text", sa.Text(), nullable=False),
        sa.Column("factor_breakdown_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("priority_score_id"),
    )
    op.create_index("ix_priority_score_records_deal_id", "priority_score_records", ["deal_id"])
    op.create_index("ix_priority_score_records_screening_id", "priority_score_records", ["screening_id"])
    op.create_index("ix_priority_score_records_priority_bucket", "priority_score_records", ["priority_bucket"])


def downgrade() -> None:
    op.drop_index("ix_priority_score_records_priority_bucket", table_name="priority_score_records")
    op.drop_index("ix_priority_score_records_screening_id", table_name="priority_score_records")
    op.drop_index("ix_priority_score_records_deal_id", table_name="priority_score_records")
    op.drop_table("priority_score_records")

