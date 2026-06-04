"""create procedure monitor tables"""

from alembic import op
import sqlalchemy as sa

revision = "067_create_procedure_monitor"
down_revision = "066_create_submission_archive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "procedure_monitor_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("procedure_monitor_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("procedure_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("procedure_monitor_set_id"),
    )
    op.create_index("ix_procedure_monitor_sets_deal_id", "procedure_monitor_sets", ["deal_id"])
    op.create_index("ix_procedure_monitor_sets_status", "procedure_monitor_sets", ["procedure_status"])

    op.create_table(
        "procedure_monitor_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("procedure_monitor_id", sa.String(length=64), nullable=False),
        sa.Column(
            "procedure_monitor_set_id",
            sa.String(length=64),
            sa.ForeignKey("procedure_monitor_sets.procedure_monitor_set_id"),
            nullable=False,
        ),
        sa.Column("current_stage", sa.Text(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("procedure_monitor_id"),
    )
    op.create_index("ix_procedure_monitor_records_set_id", "procedure_monitor_records", ["procedure_monitor_set_id"])

    op.create_table(
        "procedure_monitor_events",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("procedure_event_id", sa.String(length=64), nullable=False),
        sa.Column(
            "procedure_monitor_id",
            sa.String(length=64),
            sa.ForeignKey("procedure_monitor_records.procedure_monitor_id"),
            nullable=False,
        ),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("procedure_event_id"),
    )
    op.create_index("ix_procedure_monitor_events_monitor_id", "procedure_monitor_events", ["procedure_monitor_id"])
    op.create_index("ix_procedure_monitor_events_event_timestamp", "procedure_monitor_events", ["event_timestamp"])

    op.create_table(
        "procedure_monitor_alerts",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "procedure_monitor_id",
            sa.String(length=64),
            sa.ForeignKey("procedure_monitor_records.procedure_monitor_id"),
            nullable=False,
        ),
        sa.Column("alert_code", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_procedure_monitor_alerts_monitor_id", "procedure_monitor_alerts", ["procedure_monitor_id"])
    op.create_index("ix_procedure_monitor_alerts_severity", "procedure_monitor_alerts", ["severity"])


def downgrade() -> None:
    op.drop_index("ix_procedure_monitor_alerts_severity", table_name="procedure_monitor_alerts")
    op.drop_index("ix_procedure_monitor_alerts_monitor_id", table_name="procedure_monitor_alerts")
    op.drop_table("procedure_monitor_alerts")
    op.drop_index("ix_procedure_monitor_events_event_timestamp", table_name="procedure_monitor_events")
    op.drop_index("ix_procedure_monitor_events_monitor_id", table_name="procedure_monitor_events")
    op.drop_table("procedure_monitor_events")
    op.drop_index("ix_procedure_monitor_records_set_id", table_name="procedure_monitor_records")
    op.drop_table("procedure_monitor_records")
    op.drop_index("ix_procedure_monitor_sets_status", table_name="procedure_monitor_sets")
    op.drop_index("ix_procedure_monitor_sets_deal_id", table_name="procedure_monitor_sets")
    op.drop_table("procedure_monitor_sets")
