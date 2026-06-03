"""create document requirement tables"""

from alembic import op
import sqlalchemy as sa

revision = "012_create_document_requirements"
down_revision = "011_create_compliance_matrix"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_requirement_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("document_requirement_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("intake_id", sa.String(length=64), sa.ForeignKey("tender_intake_records.intake_id"), nullable=False),
        sa.Column("document_set_id", sa.String(length=64), sa.ForeignKey("document_sets.document_set_id"), nullable=False),
        sa.Column("tender_summary_id", sa.String(length=64), sa.ForeignKey("tender_summaries.tender_summary_id"), nullable=False),
        sa.Column("requirement_count", sa.Integer(), nullable=False),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_requirement_set_id"),
    )
    op.create_index("ix_document_requirement_sets_deal_id", "document_requirement_sets", ["deal_id"])
    op.create_index("ix_document_requirement_sets_document_set_id", "document_requirement_sets", ["document_set_id"])

    op.create_table(
        "document_requirement_rows",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("document_requirement_set_id", sa.String(length=64), sa.ForeignKey("document_requirement_sets.document_requirement_set_id"), nullable=False),
        sa.Column("row_code", sa.String(length=32), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("requirement_title", sa.Text(), nullable=False),
        sa.Column("requirement_description", sa.Text(), nullable=False),
        sa.Column("requirement_category", sa.Text(), nullable=False),
        sa.Column("requirement_status", sa.Text(), nullable=False),
        sa.Column("source_artifact_ref", sa.String(length=64), sa.ForeignKey("document_artifacts.artifact_ref"), nullable=True),
        sa.Column("source_pointer", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_requirement_set_id", "row_code", name="uq_document_requirement_rows_code"),
    )
    op.create_index("ix_document_requirement_rows_set_id", "document_requirement_rows", ["document_requirement_set_id"])
    op.create_index("ix_document_requirement_rows_status", "document_requirement_rows", ["requirement_status"])
    op.create_index("ix_document_requirement_rows_source_artifact_ref", "document_requirement_rows", ["source_artifact_ref"])


def downgrade() -> None:
    op.drop_index("ix_document_requirement_rows_source_artifact_ref", table_name="document_requirement_rows")
    op.drop_index("ix_document_requirement_rows_status", table_name="document_requirement_rows")
    op.drop_index("ix_document_requirement_rows_set_id", table_name="document_requirement_rows")
    op.drop_table("document_requirement_rows")
    op.drop_index("ix_document_requirement_sets_document_set_id", table_name="document_requirement_sets")
    op.drop_index("ix_document_requirement_sets_deal_id", table_name="document_requirement_sets")
    op.drop_table("document_requirement_sets")

