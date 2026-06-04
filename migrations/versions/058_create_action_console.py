"""create action console tables"""

from alembic import op
import sqlalchemy as sa

revision = "058_create_action_console"
down_revision = "057_create_vendor_connector_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "action_console_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("action_console_set_id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_ref", sa.String(length=128), nullable=False),
        sa.Column("console_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("action_console_set_id"),
    )
    op.create_index("ix_action_console_sets_scope_type", "action_console_sets", ["scope_type"])
    op.create_index("ix_action_console_sets_scope_ref", "action_console_sets", ["scope_ref"])

    op.create_table(
        "action_console_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("action_console_id", sa.String(length=64), nullable=False),
        sa.Column(
            "action_console_set_id",
            sa.String(length=64),
            sa.ForeignKey("action_console_sets.action_console_set_id"),
            nullable=False,
        ),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("action_console_id"),
    )
    op.create_index("ix_action_console_records_set_id", "action_console_records", ["action_console_set_id"])

    op.create_table(
        "action_console_items",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "action_console_id",
            sa.String(length=64),
            sa.ForeignKey("action_console_records.action_console_id"),
            nullable=False,
        ),
        sa.Column("item_code", sa.String(length=64), nullable=False),
        sa.Column("item_type", sa.Text(), nullable=False),
        sa.Column("priority", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.String(length=128), nullable=True),
        sa.Column("item_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_action_console_items_action_console_id", "action_console_items", ["action_console_id"])
    op.create_index("ix_action_console_items_item_type", "action_console_items", ["item_type"])
    op.create_index("ix_action_console_items_priority", "action_console_items", ["priority"])


def downgrade() -> None:
    op.drop_index("ix_action_console_items_priority", table_name="action_console_items")
    op.drop_index("ix_action_console_items_item_type", table_name="action_console_items")
    op.drop_index("ix_action_console_items_action_console_id", table_name="action_console_items")
    op.drop_table("action_console_items")
    op.drop_index("ix_action_console_records_set_id", table_name="action_console_records")
    op.drop_table("action_console_records")
    op.drop_index("ix_action_console_sets_scope_ref", table_name="action_console_sets")
    op.drop_index("ix_action_console_sets_scope_type", table_name="action_console_sets")
    op.drop_table("action_console_sets")
