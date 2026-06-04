"""create contract negotiation tables"""

from alembic import op
import sqlalchemy as sa

revision = "068_create_contract_negotiation"
down_revision = "067_create_procedure_monitor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contract_negotiation_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("contract_negotiation_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("negotiation_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("contract_negotiation_set_id"),
    )
    op.create_index("ix_contract_negotiation_sets_deal_id", "contract_negotiation_sets", ["deal_id"])
    op.create_index("ix_contract_negotiation_sets_status", "contract_negotiation_sets", ["negotiation_status"])

    op.create_table(
        "contract_negotiation_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("contract_negotiation_id", sa.String(length=64), nullable=False),
        sa.Column(
            "contract_negotiation_set_id",
            sa.String(length=64),
            sa.ForeignKey("contract_negotiation_sets.contract_negotiation_set_id"),
            nullable=False,
        ),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("negotiation_pack_manifest_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("contract_negotiation_id"),
    )
    op.create_index(
        "ix_contract_negotiation_records_set_id",
        "contract_negotiation_records",
        ["contract_negotiation_set_id"],
    )

    op.create_table(
        "contract_negotiation_issues",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "contract_negotiation_id",
            sa.String(length=64),
            sa.ForeignKey("contract_negotiation_records.contract_negotiation_id"),
            nullable=False,
        ),
        sa.Column("issue_code", sa.String(length=64), nullable=False),
        sa.Column("issue_text", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_contract_negotiation_issues_contract_negotiation_id",
        "contract_negotiation_issues",
        ["contract_negotiation_id"],
    )
    op.create_index("ix_contract_negotiation_issues_severity", "contract_negotiation_issues", ["severity"])

    op.create_table(
        "contract_negotiation_comments",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "contract_negotiation_id",
            sa.String(length=64),
            sa.ForeignKey("contract_negotiation_records.contract_negotiation_id"),
            nullable=False,
        ),
        sa.Column("clause_ref", sa.String(length=128), nullable=False),
        sa.Column("comment_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_contract_negotiation_comments_contract_negotiation_id",
        "contract_negotiation_comments",
        ["contract_negotiation_id"],
    )
    op.create_index("ix_contract_negotiation_comments_clause_ref", "contract_negotiation_comments", ["clause_ref"])


def downgrade() -> None:
    op.drop_index("ix_contract_negotiation_comments_clause_ref", table_name="contract_negotiation_comments")
    op.drop_index(
        "ix_contract_negotiation_comments_contract_negotiation_id",
        table_name="contract_negotiation_comments",
    )
    op.drop_table("contract_negotiation_comments")
    op.drop_index("ix_contract_negotiation_issues_severity", table_name="contract_negotiation_issues")
    op.drop_index(
        "ix_contract_negotiation_issues_contract_negotiation_id",
        table_name="contract_negotiation_issues",
    )
    op.drop_table("contract_negotiation_issues")
    op.drop_index(
        "ix_contract_negotiation_records_set_id",
        table_name="contract_negotiation_records",
    )
    op.drop_table("contract_negotiation_records")
    op.drop_index("ix_contract_negotiation_sets_status", table_name="contract_negotiation_sets")
    op.drop_index("ix_contract_negotiation_sets_deal_id", table_name="contract_negotiation_sets")
    op.drop_table("contract_negotiation_sets")
