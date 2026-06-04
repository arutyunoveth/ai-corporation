"""create connector registry tables"""

from alembic import op
import sqlalchemy as sa

revision = "051_create_connector_registry"
down_revision = "050_create_copilot_feed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connector_registry_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("connector_registry_set_id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_ref", sa.String(length=128), nullable=False),
        sa.Column("registry_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("connector_registry_set_id"),
    )
    op.create_index("ix_connector_registry_sets_scope_type", "connector_registry_sets", ["scope_type"])
    op.create_index("ix_connector_registry_sets_scope_ref", "connector_registry_sets", ["scope_ref"])

    op.create_table(
        "connector_registry_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("connector_registry_id", sa.String(length=64), nullable=False),
        sa.Column(
            "connector_registry_set_id",
            sa.String(length=64),
            sa.ForeignKey("connector_registry_sets.connector_registry_set_id"),
            nullable=False,
        ),
        sa.Column("connector_code", sa.String(length=64), nullable=False),
        sa.Column("connector_type", sa.Text(), nullable=False),
        sa.Column("connector_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("connector_registry_id"),
    )
    op.create_index("ix_connector_registry_records_set_id", "connector_registry_records", ["connector_registry_set_id"])
    op.create_index(
        "ix_connector_registry_records_connector_type",
        "connector_registry_records",
        ["connector_type"],
    )
    op.create_index(
        "ix_connector_registry_records_connector_status",
        "connector_registry_records",
        ["connector_status"],
    )

    op.create_table(
        "connector_sync_runs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("connector_sync_run_id", sa.String(length=64), nullable=False),
        sa.Column(
            "connector_registry_id",
            sa.String(length=64),
            sa.ForeignKey("connector_registry_records.connector_registry_id"),
            nullable=False,
        ),
        sa.Column("sync_status", sa.Text(), nullable=False),
        sa.Column("sync_summary", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("connector_sync_run_id"),
    )
    op.create_index(
        "ix_connector_sync_runs_connector_registry_id",
        "connector_sync_runs",
        ["connector_registry_id"],
    )
    op.create_index("ix_connector_sync_runs_sync_status", "connector_sync_runs", ["sync_status"])


def downgrade() -> None:
    op.drop_index("ix_connector_sync_runs_sync_status", table_name="connector_sync_runs")
    op.drop_index("ix_connector_sync_runs_connector_registry_id", table_name="connector_sync_runs")
    op.drop_table("connector_sync_runs")
    op.drop_index(
        "ix_connector_registry_records_connector_status",
        table_name="connector_registry_records",
    )
    op.drop_index(
        "ix_connector_registry_records_connector_type",
        table_name="connector_registry_records",
    )
    op.drop_index("ix_connector_registry_records_set_id", table_name="connector_registry_records")
    op.drop_table("connector_registry_records")
    op.drop_index("ix_connector_registry_sets_scope_ref", table_name="connector_registry_sets")
    op.drop_index("ix_connector_registry_sets_scope_type", table_name="connector_registry_sets")
    op.drop_table("connector_registry_sets")
