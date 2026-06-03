"""create contract risk tables"""

from alembic import op
import sqlalchemy as sa

revision = "025_create_contract_risk"
down_revision = "024_create_finance_memo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contract_risk_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("contract_risk_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("document_set_id", sa.String(length=64), sa.ForeignKey("document_sets.document_set_id"), nullable=False),
        sa.Column("risk_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("contract_risk_set_id"),
    )
    op.create_index("ix_contract_risk_sets_deal_id", "contract_risk_sets", ["deal_id"])
    op.create_index("ix_contract_risk_sets_document_set_id", "contract_risk_sets", ["document_set_id"])

    op.create_table(
        "contract_risk_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("contract_risk_id", sa.String(length=64), nullable=False),
        sa.Column(
            "contract_risk_set_id",
            sa.String(length=64),
            sa.ForeignKey("contract_risk_sets.contract_risk_set_id"),
            nullable=False,
        ),
        sa.Column("source_artifact_ref", sa.String(length=64), sa.ForeignKey("document_artifacts.artifact_ref"), nullable=True),
        sa.Column("clause_type", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("contract_risk_id"),
    )
    op.create_index("ix_contract_risk_records_set_id", "contract_risk_records", ["contract_risk_set_id"])
    op.create_index(
        "ix_contract_risk_records_source_artifact_ref",
        "contract_risk_records",
        ["source_artifact_ref"],
    )
    op.create_index("ix_contract_risk_records_clause_type", "contract_risk_records", ["clause_type"])

    op.create_table(
        "contract_risk_flags",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("contract_risk_id", sa.String(length=64), sa.ForeignKey("contract_risk_records.contract_risk_id"), nullable=False),
        sa.Column("flag_code", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_contract_risk_flags_contract_risk_id", "contract_risk_flags", ["contract_risk_id"])
    op.create_index("ix_contract_risk_flags_severity", "contract_risk_flags", ["severity"])


def downgrade() -> None:
    op.drop_index("ix_contract_risk_flags_severity", table_name="contract_risk_flags")
    op.drop_index("ix_contract_risk_flags_contract_risk_id", table_name="contract_risk_flags")
    op.drop_table("contract_risk_flags")
    op.drop_index("ix_contract_risk_records_clause_type", table_name="contract_risk_records")
    op.drop_index("ix_contract_risk_records_source_artifact_ref", table_name="contract_risk_records")
    op.drop_index("ix_contract_risk_records_set_id", table_name="contract_risk_records")
    op.drop_table("contract_risk_records")
    op.drop_index("ix_contract_risk_sets_document_set_id", table_name="contract_risk_sets")
    op.drop_index("ix_contract_risk_sets_deal_id", table_name="contract_risk_sets")
    op.drop_table("contract_risk_sets")
