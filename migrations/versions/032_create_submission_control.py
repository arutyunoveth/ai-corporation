"""create submission control tables"""

from alembic import op
import sqlalchemy as sa

revision = "032_create_submission_control"
down_revision = "031_create_submission_readiness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "submission_execution_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("submission_execution_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "submission_readiness_set_id",
            sa.String(length=64),
            sa.ForeignKey("submission_readiness_sets.submission_readiness_set_id"),
            nullable=False,
        ),
        sa.Column(
            "bid_package_set_id",
            sa.String(length=64),
            sa.ForeignKey("bid_package_sets.bid_package_set_id"),
            nullable=False,
        ),
        sa.Column("execution_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("submission_execution_set_id"),
    )
    op.create_index("ix_submission_execution_sets_deal_id", "submission_execution_sets", ["deal_id"])
    op.create_index(
        "ix_submission_execution_sets_readiness_set_id",
        "submission_execution_sets",
        ["submission_readiness_set_id"],
    )
    op.create_index(
        "ix_submission_execution_sets_bid_package_set_id",
        "submission_execution_sets",
        ["bid_package_set_id"],
    )

    op.create_table(
        "submission_execution_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("submission_execution_id", sa.String(length=64), nullable=False),
        sa.Column(
            "submission_execution_set_id",
            sa.String(length=64),
            sa.ForeignKey("submission_execution_sets.submission_execution_set_id"),
            nullable=False,
        ),
        sa.Column("channel_type", sa.Text(), nullable=False),
        sa.Column("initiated_by_ref", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("submission_execution_id"),
    )
    op.create_index(
        "ix_submission_execution_records_set_id",
        "submission_execution_records",
        ["submission_execution_set_id"],
    )

    op.create_table(
        "submission_attempts",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("submission_attempt_id", sa.String(length=64), nullable=False),
        sa.Column(
            "submission_execution_id",
            sa.String(length=64),
            sa.ForeignKey("submission_execution_records.submission_execution_id"),
            nullable=False,
        ),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("attempt_status", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("submission_attempt_id"),
    )
    op.create_index("ix_submission_attempts_submission_execution_id", "submission_attempts", ["submission_execution_id"])
    op.create_index("ix_submission_attempts_attempt_no", "submission_attempts", ["attempt_no"])


def downgrade() -> None:
    op.drop_index("ix_submission_attempts_attempt_no", table_name="submission_attempts")
    op.drop_index("ix_submission_attempts_submission_execution_id", table_name="submission_attempts")
    op.drop_table("submission_attempts")
    op.drop_index("ix_submission_execution_records_set_id", table_name="submission_execution_records")
    op.drop_table("submission_execution_records")
    op.drop_index("ix_submission_execution_sets_bid_package_set_id", table_name="submission_execution_sets")
    op.drop_index("ix_submission_execution_sets_readiness_set_id", table_name="submission_execution_sets")
    op.drop_index("ix_submission_execution_sets_deal_id", table_name="submission_execution_sets")
    op.drop_table("submission_execution_sets")
