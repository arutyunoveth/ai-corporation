"""create tender intake tables"""

from alembic import op
import sqlalchemy as sa

revision = "006_create_tender_intake"
down_revision = "005_seed_status_transition_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tender_intake_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("intake_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_channel", sa.Text(), nullable=False),
        sa.Column("source_title", sa.Text(), nullable=False),
        sa.Column("source_customer_name", sa.Text(), nullable=False),
        sa.Column("source_procurement_number", sa.Text(), nullable=True),
        sa.Column("intake_status", sa.Text(), nullable=False),
        sa.Column("duplicate_hint", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("normalized_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("intake_id"),
    )
    op.create_index("ix_tender_intake_records_deal_id", "tender_intake_records", ["deal_id"])
    op.create_index("ix_tender_intake_records_source_type", "tender_intake_records", ["source_type"])
    op.create_index(
        "ix_tender_intake_records_source_proc_number",
        "tender_intake_records",
        ["source_procurement_number"],
    )
    op.create_index("ix_tender_intake_records_received_at", "tender_intake_records", ["received_at"])

    op.create_table(
        "tender_source_payloads",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("intake_id", sa.String(length=64), sa.ForeignKey("tender_intake_records.intake_id"), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tender_source_payloads_intake_id", "tender_source_payloads", ["intake_id"])
    op.create_index("ix_tender_source_payloads_payload_hash", "tender_source_payloads", ["payload_hash"])


def downgrade() -> None:
    op.drop_index("ix_tender_source_payloads_payload_hash", table_name="tender_source_payloads")
    op.drop_index("ix_tender_source_payloads_intake_id", table_name="tender_source_payloads")
    op.drop_table("tender_source_payloads")
    op.drop_index("ix_tender_intake_records_received_at", table_name="tender_intake_records")
    op.drop_index("ix_tender_intake_records_source_proc_number", table_name="tender_intake_records")
    op.drop_index("ix_tender_intake_records_source_type", table_name="tender_intake_records")
    op.drop_index("ix_tender_intake_records_deal_id", table_name="tender_intake_records")
    op.drop_table("tender_intake_records")

