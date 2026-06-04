"""create action queue tables"""

from alembic import op
import sqlalchemy as sa

revision = "053_create_action_queue"
down_revision = "052_create_workspace_feed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "action_queue_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("action_queue_set_id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_ref", sa.String(length=128), nullable=False),
        sa.Column("queue_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("action_queue_set_id"),
    )
    op.create_index("ix_action_queue_sets_scope_type", "action_queue_sets", ["scope_type"])
    op.create_index("ix_action_queue_sets_scope_ref", "action_queue_sets", ["scope_ref"])

    op.create_table(
        "action_queue_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("action_queue_id", sa.String(length=64), nullable=False),
        sa.Column(
            "action_queue_set_id",
            sa.String(length=64),
            sa.ForeignKey("action_queue_sets.action_queue_set_id"),
            nullable=False,
        ),
        sa.Column("action_code", sa.String(length=64), nullable=False),
        sa.Column("action_type", sa.Text(), nullable=False),
        sa.Column("action_status", sa.Text(), nullable=False),
        sa.Column("action_text", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("action_queue_id"),
    )
    op.create_index("ix_action_queue_records_set_id", "action_queue_records", ["action_queue_set_id"])
    op.create_index("ix_action_queue_records_action_type", "action_queue_records", ["action_type"])
    op.create_index("ix_action_queue_records_action_status", "action_queue_records", ["action_status"])

    op.create_table(
        "action_queue_approvals",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "action_queue_id",
            sa.String(length=64),
            sa.ForeignKey("action_queue_records.action_queue_id"),
            nullable=False,
        ),
        sa.Column("approval_status", sa.Text(), nullable=False),
        sa.Column("approved_by_ref", sa.String(length=128), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_action_queue_approvals_action_queue_id", "action_queue_approvals", ["action_queue_id"])
    op.create_index("ix_action_queue_approvals_approval_status", "action_queue_approvals", ["approval_status"])


def downgrade() -> None:
    op.drop_index("ix_action_queue_approvals_approval_status", table_name="action_queue_approvals")
    op.drop_index("ix_action_queue_approvals_action_queue_id", table_name="action_queue_approvals")
    op.drop_table("action_queue_approvals")
    op.drop_index("ix_action_queue_records_action_status", table_name="action_queue_records")
    op.drop_index("ix_action_queue_records_action_type", table_name="action_queue_records")
    op.drop_index("ix_action_queue_records_set_id", table_name="action_queue_records")
    op.drop_table("action_queue_records")
    op.drop_index("ix_action_queue_sets_scope_ref", table_name="action_queue_sets")
    op.drop_index("ix_action_queue_sets_scope_type", table_name="action_queue_sets")
    op.drop_table("action_queue_sets")
