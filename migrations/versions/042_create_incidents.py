"""create incident tables"""

from alembic import op
import sqlalchemy as sa

revision = "042_create_incidents"
down_revision = "041_create_payment_collection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incident_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("incident_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "execution_command_set_id",
            sa.String(length=64),
            sa.ForeignKey("execution_command_sets.execution_command_set_id"),
            nullable=False,
        ),
        sa.Column("incident_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("incident_set_id"),
    )
    op.create_index("ix_incident_sets_deal_id", "incident_sets", ["deal_id"])
    op.create_index("ix_incident_sets_execution_command_set_id", "incident_sets", ["execution_command_set_id"])

    op.create_table(
        "incident_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("incident_id", sa.String(length=64), nullable=False),
        sa.Column(
            "incident_set_id",
            sa.String(length=64),
            sa.ForeignKey("incident_sets.incident_set_id"),
            nullable=False,
        ),
        sa.Column("incident_type", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("incident_id"),
    )
    op.create_index("ix_incident_records_set_id", "incident_records", ["incident_set_id"])
    op.create_index("ix_incident_records_incident_type", "incident_records", ["incident_type"])

    op.create_table(
        "escalation_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("escalation_id", sa.String(length=64), nullable=False),
        sa.Column(
            "incident_id",
            sa.String(length=64),
            sa.ForeignKey("incident_records.incident_id"),
            nullable=False,
        ),
        sa.Column("escalation_level", sa.Text(), nullable=False),
        sa.Column("escalation_status", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("escalation_id"),
    )
    op.create_index("ix_escalation_records_incident_id", "escalation_records", ["incident_id"])
    op.create_index("ix_escalation_records_escalation_level", "escalation_records", ["escalation_level"])


def downgrade() -> None:
    op.drop_index("ix_escalation_records_escalation_level", table_name="escalation_records")
    op.drop_index("ix_escalation_records_incident_id", table_name="escalation_records")
    op.drop_table("escalation_records")
    op.drop_index("ix_incident_records_incident_type", table_name="incident_records")
    op.drop_index("ix_incident_records_set_id", table_name="incident_records")
    op.drop_table("incident_records")
    op.drop_index("ix_incident_sets_execution_command_set_id", table_name="incident_sets")
    op.drop_index("ix_incident_sets_deal_id", table_name="incident_sets")
    op.drop_table("incident_sets")
