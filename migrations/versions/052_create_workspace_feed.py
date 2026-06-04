"""create workspace feed tables"""

from alembic import op
import sqlalchemy as sa

revision = "052_create_workspace_feed"
down_revision = "051_create_connector_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_feed_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("workspace_feed_set_id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_ref", sa.String(length=128), nullable=False),
        sa.Column("workspace_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_feed_set_id"),
    )
    op.create_index("ix_workspace_feed_sets_scope_type", "workspace_feed_sets", ["scope_type"])
    op.create_index("ix_workspace_feed_sets_scope_ref", "workspace_feed_sets", ["scope_ref"])

    op.create_table(
        "workspace_feed_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("workspace_feed_id", sa.String(length=64), nullable=False),
        sa.Column(
            "workspace_feed_set_id",
            sa.String(length=64),
            sa.ForeignKey("workspace_feed_sets.workspace_feed_set_id"),
            nullable=False,
        ),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_feed_id"),
    )
    op.create_index("ix_workspace_feed_records_set_id", "workspace_feed_records", ["workspace_feed_set_id"])

    op.create_table(
        "workspace_feed_items",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "workspace_feed_id",
            sa.String(length=64),
            sa.ForeignKey("workspace_feed_records.workspace_feed_id"),
            nullable=False,
        ),
        sa.Column("item_code", sa.String(length=64), nullable=False),
        sa.Column("item_type", sa.Text(), nullable=False),
        sa.Column("priority", sa.Text(), nullable=False),
        sa.Column("item_text", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workspace_feed_items_feed_id", "workspace_feed_items", ["workspace_feed_id"])
    op.create_index("ix_workspace_feed_items_item_type", "workspace_feed_items", ["item_type"])
    op.create_index("ix_workspace_feed_items_priority", "workspace_feed_items", ["priority"])


def downgrade() -> None:
    op.drop_index("ix_workspace_feed_items_priority", table_name="workspace_feed_items")
    op.drop_index("ix_workspace_feed_items_item_type", table_name="workspace_feed_items")
    op.drop_index("ix_workspace_feed_items_feed_id", table_name="workspace_feed_items")
    op.drop_table("workspace_feed_items")
    op.drop_index("ix_workspace_feed_records_set_id", table_name="workspace_feed_records")
    op.drop_table("workspace_feed_records")
    op.drop_index("ix_workspace_feed_sets_scope_ref", table_name="workspace_feed_sets")
    op.drop_index("ix_workspace_feed_sets_scope_type", table_name="workspace_feed_sets")
    op.drop_table("workspace_feed_sets")
