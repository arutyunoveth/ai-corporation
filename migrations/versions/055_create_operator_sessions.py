"""create operator session tables"""

from alembic import op
import sqlalchemy as sa

revision = "055_create_operator_sessions"
down_revision = "054_create_integration_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operator_session_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("operator_session_set_id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_ref", sa.String(length=128), nullable=False),
        sa.Column("session_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("operator_session_set_id"),
    )
    op.create_index("ix_operator_session_sets_scope_type", "operator_session_sets", ["scope_type"])
    op.create_index("ix_operator_session_sets_scope_ref", "operator_session_sets", ["scope_ref"])

    op.create_table(
        "operator_session_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("operator_session_id", sa.String(length=64), nullable=False),
        sa.Column(
            "operator_session_set_id",
            sa.String(length=64),
            sa.ForeignKey("operator_session_sets.operator_session_set_id"),
            nullable=False,
        ),
        sa.Column("opened_by_ref", sa.String(length=128), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("operator_session_id"),
    )
    op.create_index("ix_operator_session_records_set_id", "operator_session_records", ["operator_session_set_id"])

    op.create_table(
        "operator_session_items",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "operator_session_id",
            sa.String(length=64),
            sa.ForeignKey("operator_session_records.operator_session_id"),
            nullable=False,
        ),
        sa.Column("item_code", sa.String(length=64), nullable=False),
        sa.Column("item_type", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.String(length=128), nullable=True),
        sa.Column("item_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_operator_session_items_operator_session_id", "operator_session_items", ["operator_session_id"])
    op.create_index("ix_operator_session_items_item_type", "operator_session_items", ["item_type"])
    op.create_index("ix_operator_session_items_item_status", "operator_session_items", ["item_status"])


def downgrade() -> None:
    op.drop_index("ix_operator_session_items_item_status", table_name="operator_session_items")
    op.drop_index("ix_operator_session_items_item_type", table_name="operator_session_items")
    op.drop_index("ix_operator_session_items_operator_session_id", table_name="operator_session_items")
    op.drop_table("operator_session_items")
    op.drop_index("ix_operator_session_records_set_id", table_name="operator_session_records")
    op.drop_table("operator_session_records")
    op.drop_index("ix_operator_session_sets_scope_ref", table_name="operator_session_sets")
    op.drop_index("ix_operator_session_sets_scope_type", table_name="operator_session_sets")
    op.drop_table("operator_session_sets")
