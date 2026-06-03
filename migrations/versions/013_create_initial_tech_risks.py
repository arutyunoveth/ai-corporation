"""create initial tech risk tables"""

from alembic import op
import sqlalchemy as sa

revision = "013_create_initial_tech_risks"
down_revision = "012_create_document_requirements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "initial_tech_risk_flag_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("risk_flag_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("intake_id", sa.String(length=64), sa.ForeignKey("tender_intake_records.intake_id"), nullable=False),
        sa.Column("document_set_id", sa.String(length=64), sa.ForeignKey("document_sets.document_set_id"), nullable=False),
        sa.Column("tender_summary_id", sa.String(length=64), sa.ForeignKey("tender_summaries.tender_summary_id"), nullable=False),
        sa.Column("compliance_matrix_id", sa.String(length=64), sa.ForeignKey("compliance_matrices.compliance_matrix_id"), nullable=False),
        sa.Column("document_requirement_set_id", sa.String(length=64), sa.ForeignKey("document_requirement_sets.document_requirement_set_id"), nullable=False),
        sa.Column("risk_flag_count", sa.Integer(), nullable=False),
        sa.Column("overall_risk_severity", sa.Text(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("risk_flag_set_id"),
    )
    op.create_index("ix_initial_tech_risk_flag_sets_deal_id", "initial_tech_risk_flag_sets", ["deal_id"])
    op.create_index("ix_initial_tech_risk_flag_sets_matrix_id", "initial_tech_risk_flag_sets", ["compliance_matrix_id"])

    op.create_table(
        "initial_tech_risk_flags",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("risk_flag_set_id", sa.String(length=64), sa.ForeignKey("initial_tech_risk_flag_sets.risk_flag_set_id"), nullable=False),
        sa.Column("row_code", sa.String(length=32), nullable=False),
        sa.Column("risk_code", sa.Text(), nullable=False),
        sa.Column("risk_category", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("mitigation_hint", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("risk_flag_set_id", "row_code", name="uq_initial_tech_risk_flags_code"),
    )
    op.create_index("ix_initial_tech_risk_flags_set_id", "initial_tech_risk_flags", ["risk_flag_set_id"])
    op.create_index("ix_initial_tech_risk_flags_category", "initial_tech_risk_flags", ["risk_category"])
    op.create_index("ix_initial_tech_risk_flags_severity", "initial_tech_risk_flags", ["severity"])


def downgrade() -> None:
    op.drop_index("ix_initial_tech_risk_flags_severity", table_name="initial_tech_risk_flags")
    op.drop_index("ix_initial_tech_risk_flags_category", table_name="initial_tech_risk_flags")
    op.drop_index("ix_initial_tech_risk_flags_set_id", table_name="initial_tech_risk_flags")
    op.drop_table("initial_tech_risk_flags")
    op.drop_index("ix_initial_tech_risk_flag_sets_matrix_id", table_name="initial_tech_risk_flag_sets")
    op.drop_index("ix_initial_tech_risk_flag_sets_deal_id", table_name="initial_tech_risk_flag_sets")
    op.drop_table("initial_tech_risk_flag_sets")
