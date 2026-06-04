"""create supplier progress tables

Revision ID: 072_create_supplier_progress
Revises: 071_create_purchase_orders
Create Date: 2026-06-04 09:45:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "072_create_supplier_progress"
down_revision: str | Sequence[str] | None = "071_create_purchase_orders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "supplier_progress_sets",
        sa.Column("supplier_progress_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), nullable=False),
        sa.Column("supplier_id", sa.String(length=64), nullable=False),
        sa.Column("progress_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.deal_id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["supplier_profiles.supplier_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supplier_progress_set_id"),
    )
    op.create_index("ix_supplier_progress_sets_deal_id", "supplier_progress_sets", ["deal_id"])
    op.create_index("ix_supplier_progress_sets_supplier_id", "supplier_progress_sets", ["supplier_id"])

    op.create_table(
        "supplier_progress_records",
        sa.Column("supplier_progress_id", sa.String(length=64), nullable=False),
        sa.Column("supplier_progress_set_id", sa.String(length=64), nullable=False),
        sa.Column("readiness_state", sa.Text(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["supplier_progress_set_id"], ["supplier_progress_sets.supplier_progress_set_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supplier_progress_id"),
    )
    op.create_index("ix_supplier_progress_records_set_id", "supplier_progress_records", ["supplier_progress_set_id"])

    op.create_table(
        "supplier_progress_events",
        sa.Column("supplier_progress_event_id", sa.String(length=64), nullable=False),
        sa.Column("supplier_progress_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["supplier_progress_id"], ["supplier_progress_records.supplier_progress_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supplier_progress_event_id"),
    )
    op.create_index("ix_supplier_progress_events_progress_id", "supplier_progress_events", ["supplier_progress_id"])
    op.create_index(
        "ix_supplier_progress_events_event_timestamp",
        "supplier_progress_events",
        ["event_timestamp"],
    )

    op.create_table(
        "supplier_progress_alerts",
        sa.Column("supplier_progress_id", sa.String(length=64), nullable=False),
        sa.Column("alert_code", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["supplier_progress_id"], ["supplier_progress_records.supplier_progress_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_supplier_progress_alerts_progress_id", "supplier_progress_alerts", ["supplier_progress_id"])
    op.create_index("ix_supplier_progress_alerts_alert_code", "supplier_progress_alerts", ["alert_code"])


def downgrade() -> None:
    op.drop_index("ix_supplier_progress_alerts_alert_code", table_name="supplier_progress_alerts")
    op.drop_index("ix_supplier_progress_alerts_progress_id", table_name="supplier_progress_alerts")
    op.drop_table("supplier_progress_alerts")
    op.drop_index("ix_supplier_progress_events_event_timestamp", table_name="supplier_progress_events")
    op.drop_index("ix_supplier_progress_events_progress_id", table_name="supplier_progress_events")
    op.drop_table("supplier_progress_events")
    op.drop_index("ix_supplier_progress_records_set_id", table_name="supplier_progress_records")
    op.drop_table("supplier_progress_records")
    op.drop_index("ix_supplier_progress_sets_supplier_id", table_name="supplier_progress_sets")
    op.drop_index("ix_supplier_progress_sets_deal_id", table_name="supplier_progress_sets")
    op.drop_table("supplier_progress_sets")
