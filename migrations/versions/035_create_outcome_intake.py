"""create outcome intake tables"""

from alembic import op
import sqlalchemy as sa

revision = "035_create_outcome_intake"
down_revision = "034_create_post_submission_tracker"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outcome_intake_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("outcome_intake_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "post_submission_tracker_set_id",
            sa.String(length=64),
            sa.ForeignKey("post_submission_tracker_sets.post_submission_tracker_set_id"),
            nullable=False,
        ),
        sa.Column("outcome_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("outcome_intake_set_id"),
    )
    op.create_index("ix_outcome_intake_sets_deal_id", "outcome_intake_sets", ["deal_id"])
    op.create_index(
        "ix_outcome_intake_sets_tracker_set_id",
        "outcome_intake_sets",
        ["post_submission_tracker_set_id"],
    )

    op.create_table(
        "outcome_intake_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("outcome_intake_id", sa.String(length=64), nullable=False),
        sa.Column(
            "outcome_intake_set_id",
            sa.String(length=64),
            sa.ForeignKey("outcome_intake_sets.outcome_intake_set_id"),
            nullable=False,
        ),
        sa.Column("outcome_code", sa.Text(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("outcome_intake_id"),
    )
    op.create_index("ix_outcome_intake_records_set_id", "outcome_intake_records", ["outcome_intake_set_id"])
    op.create_index("ix_outcome_intake_records_effective_at", "outcome_intake_records", ["effective_at"])

    op.create_table(
        "outcome_intake_bindings",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "outcome_intake_id",
            sa.String(length=64),
            sa.ForeignKey("outcome_intake_records.outcome_intake_id"),
            nullable=False,
        ),
        sa.Column(
            "artifact_ref",
            sa.String(length=64),
            sa.ForeignKey("document_artifacts.artifact_ref"),
            nullable=False,
        ),
        sa.Column("binding_type", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_outcome_intake_bindings_outcome_intake_id", "outcome_intake_bindings", ["outcome_intake_id"])
    op.create_index("ix_outcome_intake_bindings_artifact_ref", "outcome_intake_bindings", ["artifact_ref"])


def downgrade() -> None:
    op.drop_index("ix_outcome_intake_bindings_artifact_ref", table_name="outcome_intake_bindings")
    op.drop_index("ix_outcome_intake_bindings_outcome_intake_id", table_name="outcome_intake_bindings")
    op.drop_table("outcome_intake_bindings")
    op.drop_index("ix_outcome_intake_records_effective_at", table_name="outcome_intake_records")
    op.drop_index("ix_outcome_intake_records_set_id", table_name="outcome_intake_records")
    op.drop_table("outcome_intake_records")
    op.drop_index("ix_outcome_intake_sets_tracker_set_id", table_name="outcome_intake_sets")
    op.drop_index("ix_outcome_intake_sets_deal_id", table_name="outcome_intake_sets")
    op.drop_table("outcome_intake_sets")
