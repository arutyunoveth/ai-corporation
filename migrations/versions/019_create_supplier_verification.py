"""create supplier verification tables"""

from alembic import op
import sqlalchemy as sa

revision = "019_create_supplier_verification"
down_revision = "018_create_quote_repository"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplier_verification_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("supplier_verification_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "supplier_shortlist_id",
            sa.String(length=64),
            sa.ForeignKey("supplier_shortlists.supplier_shortlist_id"),
            nullable=False,
        ),
        sa.Column("verification_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("supplier_verification_set_id"),
    )
    op.create_index("ix_supplier_verification_sets_deal_id", "supplier_verification_sets", ["deal_id"])
    op.create_index(
        "ix_supplier_verification_sets_shortlist_id",
        "supplier_verification_sets",
        ["supplier_shortlist_id"],
    )

    op.create_table(
        "supplier_verification_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("supplier_verification_id", sa.String(length=64), nullable=False),
        sa.Column(
            "supplier_verification_set_id",
            sa.String(length=64),
            sa.ForeignKey("supplier_verification_sets.supplier_verification_set_id"),
            nullable=False,
        ),
        sa.Column("supplier_id", sa.String(length=64), sa.ForeignKey("supplier_profiles.supplier_id"), nullable=False),
        sa.Column("verification_result", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("supplier_verification_id"),
    )
    op.create_index(
        "ix_supplier_verification_records_set_id",
        "supplier_verification_records",
        ["supplier_verification_set_id"],
    )
    op.create_index(
        "ix_supplier_verification_records_supplier_id",
        "supplier_verification_records",
        ["supplier_id"],
    )

    op.create_table(
        "supplier_verification_flags",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "supplier_verification_id",
            sa.String(length=64),
            sa.ForeignKey("supplier_verification_records.supplier_verification_id"),
            nullable=False,
        ),
        sa.Column("flag_code", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_supplier_verification_flags_verification_id",
        "supplier_verification_flags",
        ["supplier_verification_id"],
    )
    op.create_index("ix_supplier_verification_flags_severity", "supplier_verification_flags", ["severity"])


def downgrade() -> None:
    op.drop_index("ix_supplier_verification_flags_severity", table_name="supplier_verification_flags")
    op.drop_index(
        "ix_supplier_verification_flags_verification_id",
        table_name="supplier_verification_flags",
    )
    op.drop_table("supplier_verification_flags")
    op.drop_index(
        "ix_supplier_verification_records_supplier_id",
        table_name="supplier_verification_records",
    )
    op.drop_index(
        "ix_supplier_verification_records_set_id",
        table_name="supplier_verification_records",
    )
    op.drop_table("supplier_verification_records")
    op.drop_index(
        "ix_supplier_verification_sets_shortlist_id",
        table_name="supplier_verification_sets",
    )
    op.drop_index("ix_supplier_verification_sets_deal_id", table_name="supplier_verification_sets")
    op.drop_table("supplier_verification_sets")
