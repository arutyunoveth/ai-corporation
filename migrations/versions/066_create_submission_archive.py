"""create submission archive tables"""

from alembic import op
import sqlalchemy as sa

revision = "066_create_submission_archive"
down_revision = "065_extend_bid_completeness_with_readiness_report"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "submission_archive_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("submission_archive_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("archive_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("submission_archive_set_id"),
    )
    op.create_index("ix_submission_archive_sets_deal_id", "submission_archive_sets", ["deal_id"])
    op.create_index("ix_submission_archive_sets_archive_status", "submission_archive_sets", ["archive_status"])

    op.create_table(
        "submission_archive_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("submission_archive_id", sa.String(length=64), nullable=False),
        sa.Column(
            "submission_archive_set_id",
            sa.String(length=64),
            sa.ForeignKey("submission_archive_sets.submission_archive_set_id"),
            nullable=False,
        ),
        sa.Column("archive_manifest_json", sa.JSON(), nullable=False),
        sa.Column("proof_summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("submission_archive_id"),
    )
    op.create_index("ix_submission_archive_records_set_id", "submission_archive_records", ["submission_archive_set_id"])

    op.create_table(
        "submission_archive_items",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "submission_archive_id",
            sa.String(length=64),
            sa.ForeignKey("submission_archive_records.submission_archive_id"),
            nullable=False,
        ),
        sa.Column(
            "artifact_ref",
            sa.String(length=64),
            sa.ForeignKey("document_artifacts.artifact_ref"),
            nullable=False,
        ),
        sa.Column("item_role", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_submission_archive_items_submission_archive_id",
        "submission_archive_items",
        ["submission_archive_id"],
    )
    op.create_index("ix_submission_archive_items_artifact_ref", "submission_archive_items", ["artifact_ref"])
    op.create_index("ix_submission_archive_items_item_role", "submission_archive_items", ["item_role"])


def downgrade() -> None:
    op.drop_index("ix_submission_archive_items_item_role", table_name="submission_archive_items")
    op.drop_index("ix_submission_archive_items_artifact_ref", table_name="submission_archive_items")
    op.drop_index(
        "ix_submission_archive_items_submission_archive_id",
        table_name="submission_archive_items",
    )
    op.drop_table("submission_archive_items")
    op.drop_index("ix_submission_archive_records_set_id", table_name="submission_archive_records")
    op.drop_table("submission_archive_records")
    op.drop_index("ix_submission_archive_sets_archive_status", table_name="submission_archive_sets")
    op.drop_index("ix_submission_archive_sets_deal_id", table_name="submission_archive_sets")
    op.drop_table("submission_archive_sets")
