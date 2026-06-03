"""create deal closure tables"""

from alembic import op
import sqlalchemy as sa

revision = "043_create_deal_closure"
down_revision = "042_create_incidents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deal_closure_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("deal_closure_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "outcome_intake_set_id",
            sa.String(length=64),
            sa.ForeignKey("outcome_intake_sets.outcome_intake_set_id"),
            nullable=False,
        ),
        sa.Column(
            "execution_command_set_id",
            sa.String(length=64),
            sa.ForeignKey("execution_command_sets.execution_command_set_id"),
            nullable=False,
        ),
        sa.Column("closure_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("deal_closure_set_id"),
    )
    op.create_index("ix_deal_closure_sets_deal_id", "deal_closure_sets", ["deal_id"])
    op.create_index("ix_deal_closure_sets_outcome_intake_set_id", "deal_closure_sets", ["outcome_intake_set_id"])
    op.create_index(
        "ix_deal_closure_sets_execution_command_set_id",
        "deal_closure_sets",
        ["execution_command_set_id"],
    )

    op.create_table(
        "deal_closure_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("deal_closure_id", sa.String(length=64), nullable=False),
        sa.Column(
            "deal_closure_set_id",
            sa.String(length=64),
            sa.ForeignKey("deal_closure_sets.deal_closure_set_id"),
            nullable=False,
        ),
        sa.Column("closure_code", sa.Text(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("deal_closure_id"),
    )
    op.create_index("ix_deal_closure_records_set_id", "deal_closure_records", ["deal_closure_set_id"])
    op.create_index("ix_deal_closure_records_closed_at", "deal_closure_records", ["closed_at"])

    op.create_table(
        "deal_archive_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("archive_snapshot_id", sa.String(length=64), nullable=False),
        sa.Column(
            "deal_closure_set_id",
            sa.String(length=64),
            sa.ForeignKey("deal_closure_sets.deal_closure_set_id"),
            nullable=False,
        ),
        sa.Column("snapshot_manifest_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("archive_snapshot_id"),
    )
    op.create_index("ix_deal_archive_snapshots_set_id", "deal_archive_snapshots", ["deal_closure_set_id"])


def downgrade() -> None:
    op.drop_index("ix_deal_archive_snapshots_set_id", table_name="deal_archive_snapshots")
    op.drop_table("deal_archive_snapshots")
    op.drop_index("ix_deal_closure_records_closed_at", table_name="deal_closure_records")
    op.drop_index("ix_deal_closure_records_set_id", table_name="deal_closure_records")
    op.drop_table("deal_closure_records")
    op.drop_index("ix_deal_closure_sets_execution_command_set_id", table_name="deal_closure_sets")
    op.drop_index("ix_deal_closure_sets_outcome_intake_set_id", table_name="deal_closure_sets")
    op.drop_index("ix_deal_closure_sets_deal_id", table_name="deal_closure_sets")
    op.drop_table("deal_closure_sets")
