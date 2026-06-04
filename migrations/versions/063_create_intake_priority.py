"""create intake priority tables"""

from alembic import op
import sqlalchemy as sa

revision = "063_create_intake_priority"
down_revision = "062_create_tender_normalization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "intake_priority_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("intake_priority_set_id", sa.String(length=64), nullable=False),
        sa.Column(
            "deal_id",
            sa.String(length=32),
            sa.ForeignKey("deals.deal_id"),
            nullable=False,
        ),
        sa.Column("prioritization_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("intake_priority_set_id"),
    )
    op.create_index("ix_intake_priority_sets_deal_id", "intake_priority_sets", ["deal_id"])
    op.create_index("ix_intake_priority_sets_status", "intake_priority_sets", ["prioritization_status"])

    op.create_table(
        "intake_priority_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("intake_priority_id", sa.String(length=64), nullable=False),
        sa.Column(
            "intake_priority_set_id",
            sa.String(length=64),
            sa.ForeignKey("intake_priority_sets.intake_priority_set_id"),
            nullable=False,
        ),
        sa.Column("priority_score", sa.Float(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("recommended_queue_position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("intake_priority_id"),
    )
    op.create_index(
        "ix_intake_priority_records_set_id",
        "intake_priority_records",
        ["intake_priority_set_id"],
    )
    op.create_index(
        "ix_intake_priority_records_priority_score",
        "intake_priority_records",
        ["priority_score"],
    )

    op.create_table(
        "intake_priority_factors",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "intake_priority_id",
            sa.String(length=64),
            sa.ForeignKey("intake_priority_records.intake_priority_id"),
            nullable=False,
        ),
        sa.Column("factor_code", sa.String(length=64), nullable=False),
        sa.Column("factor_value", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_intake_priority_factors_intake_priority_id",
        "intake_priority_factors",
        ["intake_priority_id"],
    )
    op.create_index(
        "ix_intake_priority_factors_factor_code",
        "intake_priority_factors",
        ["factor_code"],
    )


def downgrade() -> None:
    op.drop_index("ix_intake_priority_factors_factor_code", table_name="intake_priority_factors")
    op.drop_index(
        "ix_intake_priority_factors_intake_priority_id",
        table_name="intake_priority_factors",
    )
    op.drop_table("intake_priority_factors")
    op.drop_index(
        "ix_intake_priority_records_priority_score",
        table_name="intake_priority_records",
    )
    op.drop_index("ix_intake_priority_records_set_id", table_name="intake_priority_records")
    op.drop_table("intake_priority_records")
    op.drop_index("ix_intake_priority_sets_status", table_name="intake_priority_sets")
    op.drop_index("ix_intake_priority_sets_deal_id", table_name="intake_priority_sets")
    op.drop_table("intake_priority_sets")
