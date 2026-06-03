"""create post submission tracker tables"""

from alembic import op
import sqlalchemy as sa

revision = "034_create_post_submission_tracker"
down_revision = "033_create_submission_receipts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "post_submission_tracker_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("post_submission_tracker_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "submission_execution_set_id",
            sa.String(length=64),
            sa.ForeignKey("submission_execution_sets.submission_execution_set_id"),
            nullable=False,
        ),
        sa.Column("tracker_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("post_submission_tracker_set_id"),
    )
    op.create_index("ix_post_submission_tracker_sets_deal_id", "post_submission_tracker_sets", ["deal_id"])
    op.create_index(
        "ix_post_submission_tracker_sets_execution_set_id",
        "post_submission_tracker_sets",
        ["submission_execution_set_id"],
    )

    op.create_table(
        "post_submission_tracker_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("post_submission_tracker_id", sa.String(length=64), nullable=False),
        sa.Column(
            "post_submission_tracker_set_id",
            sa.String(length=64),
            sa.ForeignKey("post_submission_tracker_sets.post_submission_tracker_set_id"),
            nullable=False,
        ),
        sa.Column("current_stage", sa.Text(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("post_submission_tracker_id"),
    )
    op.create_index(
        "ix_post_submission_tracker_records_set_id",
        "post_submission_tracker_records",
        ["post_submission_tracker_set_id"],
    )

    op.create_table(
        "post_submission_events",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("post_submission_event_id", sa.String(length=64), nullable=False),
        sa.Column(
            "post_submission_tracker_id",
            sa.String(length=64),
            sa.ForeignKey("post_submission_tracker_records.post_submission_tracker_id"),
            nullable=False,
        ),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("post_submission_event_id"),
    )
    op.create_index(
        "ix_post_submission_events_post_submission_tracker_id",
        "post_submission_events",
        ["post_submission_tracker_id"],
    )
    op.create_index("ix_post_submission_events_event_timestamp", "post_submission_events", ["event_timestamp"])


def downgrade() -> None:
    op.drop_index("ix_post_submission_events_event_timestamp", table_name="post_submission_events")
    op.drop_index(
        "ix_post_submission_events_post_submission_tracker_id",
        table_name="post_submission_events",
    )
    op.drop_table("post_submission_events")
    op.drop_index("ix_post_submission_tracker_records_set_id", table_name="post_submission_tracker_records")
    op.drop_table("post_submission_tracker_records")
    op.drop_index(
        "ix_post_submission_tracker_sets_execution_set_id",
        table_name="post_submission_tracker_sets",
    )
    op.drop_index("ix_post_submission_tracker_sets_deal_id", table_name="post_submission_tracker_sets")
    op.drop_table("post_submission_tracker_sets")
