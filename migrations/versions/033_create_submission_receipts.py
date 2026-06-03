"""create submission receipt tables"""

from alembic import op
import sqlalchemy as sa

revision = "033_create_submission_receipts"
down_revision = "032_create_submission_control"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "submission_receipt_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("submission_receipt_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "submission_execution_set_id",
            sa.String(length=64),
            sa.ForeignKey("submission_execution_sets.submission_execution_set_id"),
            nullable=False,
        ),
        sa.Column("receipt_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("submission_receipt_set_id"),
    )
    op.create_index("ix_submission_receipt_sets_deal_id", "submission_receipt_sets", ["deal_id"])
    op.create_index(
        "ix_submission_receipt_sets_execution_set_id",
        "submission_receipt_sets",
        ["submission_execution_set_id"],
    )

    op.create_table(
        "submission_receipt_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("submission_receipt_id", sa.String(length=64), nullable=False),
        sa.Column(
            "submission_receipt_set_id",
            sa.String(length=64),
            sa.ForeignKey("submission_receipt_sets.submission_receipt_set_id"),
            nullable=False,
        ),
        sa.Column("receipt_number", sa.String(length=128), nullable=False),
        sa.Column("receipt_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("receipt_source", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("submission_receipt_id"),
    )
    op.create_index("ix_submission_receipt_records_set_id", "submission_receipt_records", ["submission_receipt_set_id"])
    op.create_index(
        "ix_submission_receipt_records_receipt_number",
        "submission_receipt_records",
        ["receipt_number"],
    )

    op.create_table(
        "submission_receipt_bindings",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "submission_receipt_id",
            sa.String(length=64),
            sa.ForeignKey("submission_receipt_records.submission_receipt_id"),
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
    op.create_index(
        "ix_submission_receipt_bindings_submission_receipt_id",
        "submission_receipt_bindings",
        ["submission_receipt_id"],
    )
    op.create_index("ix_submission_receipt_bindings_artifact_ref", "submission_receipt_bindings", ["artifact_ref"])


def downgrade() -> None:
    op.drop_index("ix_submission_receipt_bindings_artifact_ref", table_name="submission_receipt_bindings")
    op.drop_index(
        "ix_submission_receipt_bindings_submission_receipt_id",
        table_name="submission_receipt_bindings",
    )
    op.drop_table("submission_receipt_bindings")
    op.drop_index("ix_submission_receipt_records_receipt_number", table_name="submission_receipt_records")
    op.drop_index("ix_submission_receipt_records_set_id", table_name="submission_receipt_records")
    op.drop_table("submission_receipt_records")
    op.drop_index("ix_submission_receipt_sets_execution_set_id", table_name="submission_receipt_sets")
    op.drop_index("ix_submission_receipt_sets_deal_id", table_name="submission_receipt_sets")
    op.drop_table("submission_receipt_sets")
