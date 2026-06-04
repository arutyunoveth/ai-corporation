"""create payment tracking tables

Revision ID: 077_create_payment_tracking
Revises: 076_create_closing_docs
Create Date: 2026-06-04 11:50:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "077_create_payment_tracking"
down_revision: str | Sequence[str] | None = "076_create_closing_docs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_tracking_sets",
        sa.Column("payment_tracking_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), nullable=False),
        sa.Column("payment_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.deal_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_tracking_set_id"),
    )
    op.create_index("ix_payment_tracking_sets_deal_id", "payment_tracking_sets", ["deal_id"])

    op.create_table(
        "payment_tracking_records",
        sa.Column("payment_tracking_id", sa.String(length=64), nullable=False),
        sa.Column("payment_tracking_set_id", sa.String(length=64), nullable=False),
        sa.Column("expected_amount", sa.Float(), nullable=False),
        sa.Column("paid_amount", sa.Float(), nullable=False),
        sa.Column("overdue_days", sa.Integer(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["payment_tracking_set_id"], ["payment_tracking_sets.payment_tracking_set_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_tracking_id"),
    )
    op.create_index("ix_payment_tracking_records_set_id", "payment_tracking_records", ["payment_tracking_set_id"])

    op.create_table(
        "payment_tracking_events",
        sa.Column("payment_tracking_event_id", sa.String(length=64), nullable=False),
        sa.Column("payment_tracking_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["payment_tracking_id"], ["payment_tracking_records.payment_tracking_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_tracking_event_id"),
    )
    op.create_index("ix_payment_tracking_events_tracking_id", "payment_tracking_events", ["payment_tracking_id"])
    op.create_index("ix_payment_tracking_events_event_timestamp", "payment_tracking_events", ["event_timestamp"])

    op.create_table(
        "payment_tracking_alerts",
        sa.Column("payment_tracking_id", sa.String(length=64), nullable=False),
        sa.Column("alert_code", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["payment_tracking_id"], ["payment_tracking_records.payment_tracking_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payment_tracking_alerts_tracking_id", "payment_tracking_alerts", ["payment_tracking_id"])
    op.create_index("ix_payment_tracking_alerts_alert_code", "payment_tracking_alerts", ["alert_code"])


def downgrade() -> None:
    op.drop_index("ix_payment_tracking_alerts_alert_code", table_name="payment_tracking_alerts")
    op.drop_index("ix_payment_tracking_alerts_tracking_id", table_name="payment_tracking_alerts")
    op.drop_table("payment_tracking_alerts")
    op.drop_index("ix_payment_tracking_events_event_timestamp", table_name="payment_tracking_events")
    op.drop_index("ix_payment_tracking_events_tracking_id", table_name="payment_tracking_events")
    op.drop_table("payment_tracking_events")
    op.drop_index("ix_payment_tracking_records_set_id", table_name="payment_tracking_records")
    op.drop_table("payment_tracking_records")
    op.drop_index("ix_payment_tracking_sets_deal_id", table_name="payment_tracking_sets")
    op.drop_table("payment_tracking_sets")
