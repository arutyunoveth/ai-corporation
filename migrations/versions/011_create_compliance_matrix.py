"""create compliance matrix tables"""

from alembic import op
import sqlalchemy as sa

revision = "011_create_compliance_matrix"
down_revision = "010_create_priority_scoring"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_matrices",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("compliance_matrix_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("intake_id", sa.String(length=64), sa.ForeignKey("tender_intake_records.intake_id"), nullable=False),
        sa.Column("document_set_id", sa.String(length=64), sa.ForeignKey("document_sets.document_set_id"), nullable=False),
        sa.Column("tender_summary_id", sa.String(length=64), sa.ForeignKey("tender_summaries.tender_summary_id"), nullable=False),
        sa.Column("matrix_row_count", sa.Integer(), nullable=False),
        sa.Column("ambiguous_row_count", sa.Integer(), nullable=False),
        sa.Column("high_risk_row_count", sa.Integer(), nullable=False),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("compliance_matrix_id"),
    )
    op.create_index("ix_compliance_matrices_deal_id", "compliance_matrices", ["deal_id"])
    op.create_index("ix_compliance_matrices_document_set_id", "compliance_matrices", ["document_set_id"])

    op.create_table(
        "compliance_matrix_rows",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("compliance_matrix_id", sa.String(length=64), sa.ForeignKey("compliance_matrices.compliance_matrix_id"), nullable=False),
        sa.Column("row_code", sa.String(length=32), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("requirement_category", sa.Text(), nullable=False),
        sa.Column("compliance_status", sa.Text(), nullable=False),
        sa.Column("source_artifact_ref", sa.String(length=64), sa.ForeignKey("document_artifacts.artifact_ref"), nullable=True),
        sa.Column("source_pointer", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("compliance_matrix_id", "row_code", name="uq_compliance_matrix_rows_code"),
    )
    op.create_index("ix_compliance_matrix_rows_matrix_id", "compliance_matrix_rows", ["compliance_matrix_id"])
    op.create_index("ix_compliance_matrix_rows_status", "compliance_matrix_rows", ["compliance_status"])
    op.create_index("ix_compliance_matrix_rows_source_artifact_ref", "compliance_matrix_rows", ["source_artifact_ref"])


def downgrade() -> None:
    op.drop_index("ix_compliance_matrix_rows_source_artifact_ref", table_name="compliance_matrix_rows")
    op.drop_index("ix_compliance_matrix_rows_status", table_name="compliance_matrix_rows")
    op.drop_index("ix_compliance_matrix_rows_matrix_id", table_name="compliance_matrix_rows")
    op.drop_table("compliance_matrix_rows")
    op.drop_index("ix_compliance_matrices_document_set_id", table_name="compliance_matrices")
    op.drop_index("ix_compliance_matrices_deal_id", table_name="compliance_matrices")
    op.drop_table("compliance_matrices")

