"""create tender import tables"""

from alembic import op
import sqlalchemy as sa

revision = "061_create_tender_import"
down_revision = "060_create_customer_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tender_import_runs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tender_import_run_id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("run_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tender_import_run_id"),
    )
    op.create_index("ix_tender_import_runs_source_type", "tender_import_runs", ["source_type"])
    op.create_index("ix_tender_import_runs_run_status", "tender_import_runs", ["run_status"])

    op.create_table(
        "tender_import_events",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tender_import_event_id", sa.String(length=64), nullable=False),
        sa.Column(
            "tender_import_run_id",
            sa.String(length=64),
            sa.ForeignKey("tender_import_runs.tender_import_run_id"),
            nullable=False,
        ),
        sa.Column("raw_procurement_number", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tender_import_event_id"),
    )
    op.create_index("ix_tender_import_events_run_id", "tender_import_events", ["tender_import_run_id"])
    op.create_index(
        "ix_tender_import_events_raw_procurement_number",
        "tender_import_events",
        ["raw_procurement_number"],
    )

    op.create_table(
        "tender_import_payloads",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "tender_import_event_id",
            sa.String(length=64),
            sa.ForeignKey("tender_import_events.tender_import_event_id"),
            nullable=False,
        ),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tender_import_payloads_event_id", "tender_import_payloads", ["tender_import_event_id"])
    op.create_index(
        "ix_tender_import_payloads_payload_hash",
        "tender_import_payloads",
        ["payload_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_tender_import_payloads_payload_hash", table_name="tender_import_payloads")
    op.drop_index("ix_tender_import_payloads_event_id", table_name="tender_import_payloads")
    op.drop_table("tender_import_payloads")
    op.drop_index(
        "ix_tender_import_events_raw_procurement_number",
        table_name="tender_import_events",
    )
    op.drop_index("ix_tender_import_events_run_id", table_name="tender_import_events")
    op.drop_table("tender_import_events")
    op.drop_index("ix_tender_import_runs_run_status", table_name="tender_import_runs")
    op.drop_index("ix_tender_import_runs_source_type", table_name="tender_import_runs")
    op.drop_table("tender_import_runs")
