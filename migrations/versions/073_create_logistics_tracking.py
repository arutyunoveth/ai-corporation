"""create logistics tracking tables

Revision ID: 073_create_logistics_tracking
Revises: 072_create_supplier_progress
Create Date: 2026-06-04 11:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "073_create_logistics_tracking"
down_revision: str | Sequence[str] | None = "072_create_supplier_progress"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "logistics_tracking_sets",
        sa.Column("logistics_tracking_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), nullable=False),
        sa.Column("logistics_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.deal_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("logistics_tracking_set_id"),
    )
    op.create_index("ix_logistics_tracking_sets_deal_id", "logistics_tracking_sets", ["deal_id"])

    op.create_table(
        "logistics_tracking_records",
        sa.Column("logistics_tracking_id", sa.String(length=64), nullable=False),
        sa.Column("logistics_tracking_set_id", sa.String(length=64), nullable=False),
        sa.Column("eta_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["logistics_tracking_set_id"], ["logistics_tracking_sets.logistics_tracking_set_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("logistics_tracking_id"),
    )
    op.create_index("ix_logistics_tracking_records_set_id", "logistics_tracking_records", ["logistics_tracking_set_id"])

    op.create_table(
        "logistics_tracking_events",
        sa.Column("logistics_tracking_event_id", sa.String(length=64), nullable=False),
        sa.Column("logistics_tracking_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["logistics_tracking_id"], ["logistics_tracking_records.logistics_tracking_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("logistics_tracking_event_id"),
    )
    op.create_index("ix_logistics_tracking_events_tracking_id", "logistics_tracking_events", ["logistics_tracking_id"])
    op.create_index("ix_logistics_tracking_events_event_timestamp", "logistics_tracking_events", ["event_timestamp"])

    op.create_table(
        "logistics_tracking_links",
        sa.Column("logistics_tracking_id", sa.String(length=64), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["logistics_tracking_id"], ["logistics_tracking_records.logistics_tracking_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_logistics_tracking_links_tracking_id", "logistics_tracking_links", ["logistics_tracking_id"])


def downgrade() -> None:
    op.drop_index("ix_logistics_tracking_links_tracking_id", table_name="logistics_tracking_links")
    op.drop_table("logistics_tracking_links")
    op.drop_index("ix_logistics_tracking_events_event_timestamp", table_name="logistics_tracking_events")
    op.drop_index("ix_logistics_tracking_events_tracking_id", table_name="logistics_tracking_events")
    op.drop_table("logistics_tracking_events")
    op.drop_index("ix_logistics_tracking_records_set_id", table_name="logistics_tracking_records")
    op.drop_table("logistics_tracking_records")
    op.drop_index("ix_logistics_tracking_sets_deal_id", table_name="logistics_tracking_sets")
    op.drop_table("logistics_tracking_sets")
