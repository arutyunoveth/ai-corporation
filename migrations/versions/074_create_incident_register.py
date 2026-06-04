"""create incident register tables

Revision ID: 074_create_incident_register
Revises: 073_create_logistics_tracking
Create Date: 2026-06-04 11:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "074_create_incident_register"
down_revision: str | Sequence[str] | None = "073_create_logistics_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "incident_register_sets",
        sa.Column("incident_register_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), nullable=False),
        sa.Column("incident_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.deal_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("incident_register_set_id"),
    )
    op.create_index("ix_incident_register_sets_deal_id", "incident_register_sets", ["deal_id"])

    op.create_table(
        "incident_register_records",
        sa.Column("incident_register_id", sa.String(length=64), nullable=False),
        sa.Column("incident_register_set_id", sa.String(length=64), nullable=False),
        sa.Column("incident_type", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["incident_register_set_id"], ["incident_register_sets.incident_register_set_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("incident_register_id"),
    )
    op.create_index("ix_incident_register_records_set_id", "incident_register_records", ["incident_register_set_id"])

    op.create_table(
        "incident_register_events",
        sa.Column("incident_register_event_id", sa.String(length=64), nullable=False),
        sa.Column("incident_register_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["incident_register_id"], ["incident_register_records.incident_register_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("incident_register_event_id"),
    )
    op.create_index("ix_incident_register_events_register_id", "incident_register_events", ["incident_register_id"])
    op.create_index("ix_incident_register_events_event_timestamp", "incident_register_events", ["event_timestamp"])

    op.create_table(
        "incident_register_flags",
        sa.Column("incident_register_id", sa.String(length=64), nullable=False),
        sa.Column("flag_code", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["incident_register_id"], ["incident_register_records.incident_register_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incident_register_flags_register_id", "incident_register_flags", ["incident_register_id"])
    op.create_index("ix_incident_register_flags_flag_code", "incident_register_flags", ["flag_code"])


def downgrade() -> None:
    op.drop_index("ix_incident_register_flags_flag_code", table_name="incident_register_flags")
    op.drop_index("ix_incident_register_flags_register_id", table_name="incident_register_flags")
    op.drop_table("incident_register_flags")
    op.drop_index("ix_incident_register_events_event_timestamp", table_name="incident_register_events")
    op.drop_index("ix_incident_register_events_register_id", table_name="incident_register_events")
    op.drop_table("incident_register_events")
    op.drop_index("ix_incident_register_records_set_id", table_name="incident_register_records")
    op.drop_table("incident_register_records")
    op.drop_index("ix_incident_register_sets_deal_id", table_name="incident_register_sets")
    op.drop_table("incident_register_sets")
