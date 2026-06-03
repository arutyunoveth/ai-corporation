"""create tender screening tables"""

from alembic import op
import sqlalchemy as sa

revision = "009_create_tender_screening"
down_revision = "008_create_tender_summaries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tender_screening_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("screening_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("intake_id", sa.String(length=64), sa.ForeignKey("tender_intake_records.intake_id"), nullable=False),
        sa.Column("document_set_id", sa.String(length=64), sa.ForeignKey("document_sets.document_set_id"), nullable=False),
        sa.Column("tender_summary_id", sa.String(length=64), sa.ForeignKey("tender_summaries.tender_summary_id"), nullable=False),
        sa.Column("result_status", sa.Text(), nullable=False),
        sa.Column("screening_score", sa.Float(), nullable=False),
        sa.Column("rationale_text", sa.Text(), nullable=False),
        sa.Column("factor_breakdown_json", sa.JSON(), nullable=False),
        sa.Column("reason_codes_json", sa.JSON(), nullable=False),
        sa.Column("recommended_next_status", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("screening_id"),
    )
    op.create_index("ix_tender_screening_records_deal_id", "tender_screening_records", ["deal_id"])
    op.create_index("ix_tender_screening_records_intake_id", "tender_screening_records", ["intake_id"])
    op.create_index("ix_tender_screening_records_result_status", "tender_screening_records", ["result_status"])


def downgrade() -> None:
    op.drop_index("ix_tender_screening_records_result_status", table_name="tender_screening_records")
    op.drop_index("ix_tender_screening_records_intake_id", table_name="tender_screening_records")
    op.drop_index("ix_tender_screening_records_deal_id", table_name="tender_screening_records")
    op.drop_table("tender_screening_records")

