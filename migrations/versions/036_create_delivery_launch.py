"""create delivery launch tables"""

from alembic import op
import sqlalchemy as sa

revision = "036_create_delivery_launch"
down_revision = "035_create_outcome_intake"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "delivery_launch_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("delivery_launch_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "outcome_intake_set_id",
            sa.String(length=64),
            sa.ForeignKey("outcome_intake_sets.outcome_intake_set_id"),
            nullable=False,
        ),
        sa.Column("launch_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("delivery_launch_set_id"),
    )
    op.create_index("ix_delivery_launch_sets_deal_id", "delivery_launch_sets", ["deal_id"])
    op.create_index(
        "ix_delivery_launch_sets_outcome_intake_set_id",
        "delivery_launch_sets",
        ["outcome_intake_set_id"],
    )

    op.create_table(
        "delivery_launch_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("delivery_launch_id", sa.String(length=64), nullable=False),
        sa.Column(
            "delivery_launch_set_id",
            sa.String(length=64),
            sa.ForeignKey("delivery_launch_sets.delivery_launch_set_id"),
            nullable=False,
        ),
        sa.Column("launch_recommendation", sa.Text(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("delivery_launch_id"),
    )
    op.create_index("ix_delivery_launch_records_set_id", "delivery_launch_records", ["delivery_launch_set_id"])

    op.create_table(
        "delivery_launch_flags",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "delivery_launch_id",
            sa.String(length=64),
            sa.ForeignKey("delivery_launch_records.delivery_launch_id"),
            nullable=False,
        ),
        sa.Column("flag_code", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_delivery_launch_flags_delivery_launch_id", "delivery_launch_flags", ["delivery_launch_id"])
    op.create_index("ix_delivery_launch_flags_severity", "delivery_launch_flags", ["severity"])


def downgrade() -> None:
    op.drop_index("ix_delivery_launch_flags_severity", table_name="delivery_launch_flags")
    op.drop_index("ix_delivery_launch_flags_delivery_launch_id", table_name="delivery_launch_flags")
    op.drop_table("delivery_launch_flags")
    op.drop_index("ix_delivery_launch_records_set_id", table_name="delivery_launch_records")
    op.drop_table("delivery_launch_records")
    op.drop_index("ix_delivery_launch_sets_outcome_intake_set_id", table_name="delivery_launch_sets")
    op.drop_index("ix_delivery_launch_sets_deal_id", table_name="delivery_launch_sets")
    op.drop_table("delivery_launch_sets")
