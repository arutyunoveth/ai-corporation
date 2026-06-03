"""create event log tables"""

from alembic import op
import sqlalchemy as sa

revision = "004_create_event_log"
down_revision = "003_create_document_store"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=True),
        sa.Column("event_code", sa.Text(), nullable=False),
        sa.Column("source_module_id", sa.Text(), nullable=True),
        sa.Column("source_agent_code", sa.Text(), nullable=True),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_event_records_deal_id", "event_records", ["deal_id"])
    op.create_index("ix_event_records_event_code", "event_records", ["event_code"])
    op.create_index("ix_event_records_source_module_id", "event_records", ["source_module_id"])
    op.create_index("ix_event_records_created_at", "event_records", ["created_at"])

    op.create_table(
        "decision_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("decision_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column("decision_code", sa.Text(), nullable=False),
        sa.Column("decided_by_type", sa.Text(), nullable=False),
        sa.Column("decided_by_ref", sa.Text(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("decision_id"),
    )
    op.create_index("ix_decision_records_deal_id", "decision_records", ["deal_id"])
    op.create_index("ix_decision_records_decision_code", "decision_records", ["decision_code"])


def downgrade() -> None:
    op.drop_index("ix_decision_records_decision_code", table_name="decision_records")
    op.drop_index("ix_decision_records_deal_id", table_name="decision_records")
    op.drop_table("decision_records")
    op.drop_index("ix_event_records_created_at", table_name="event_records")
    op.drop_index("ix_event_records_source_module_id", table_name="event_records")
    op.drop_index("ix_event_records_event_code", table_name="event_records")
    op.drop_index("ix_event_records_deal_id", table_name="event_records")
    op.drop_table("event_records")

