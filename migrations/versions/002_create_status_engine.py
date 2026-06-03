"""create status engine tables"""

from alembic import op
import sqlalchemy as sa

revision = "002_create_status_engine"
down_revision = "001_create_deal_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "status_transition_rules",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("from_status", sa.Text(), nullable=False),
        sa.Column("to_status", sa.Text(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("transition_type", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("from_status", "to_status", name="uq_status_transition_rules_pair"),
    )

    op.create_table(
        "deal_status_history",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("from_status", sa.Text(), nullable=True),
        sa.Column("to_status", sa.Text(), nullable=False),
        sa.Column("changed_by_type", sa.Text(), nullable=False),
        sa.Column("changed_by_ref", sa.Text(), nullable=True),
        sa.Column("reason_code", sa.Text(), nullable=True),
        sa.Column("reason_text", sa.Text(), nullable=True),
        sa.Column("is_override", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_deal_status_history_deal_id", "deal_status_history", ["deal_id"])
    op.create_index("ix_deal_status_history_to_status", "deal_status_history", ["to_status"])
    op.create_index("ix_deal_status_history_created_at", "deal_status_history", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_deal_status_history_created_at", table_name="deal_status_history")
    op.drop_index("ix_deal_status_history_to_status", table_name="deal_status_history")
    op.drop_index("ix_deal_status_history_deal_id", table_name="deal_status_history")
    op.drop_table("deal_status_history")
    op.drop_table("status_transition_rules")

