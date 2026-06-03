"""create dashboard snapshot tables"""

from alembic import op
import sqlalchemy as sa

revision = "045_create_dashboard_snapshots"
down_revision = "044_create_kpi_learning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dashboard_snapshot_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("dashboard_snapshot_set_id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_ref", sa.String(length=128), nullable=False),
        sa.Column("snapshot_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dashboard_snapshot_set_id"),
    )
    op.create_index("ix_dashboard_snapshot_sets_scope_type", "dashboard_snapshot_sets", ["scope_type"])
    op.create_index("ix_dashboard_snapshot_sets_scope_ref", "dashboard_snapshot_sets", ["scope_ref"])

    op.create_table(
        "dashboard_snapshot_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("dashboard_snapshot_id", sa.String(length=64), nullable=False),
        sa.Column(
            "dashboard_snapshot_set_id",
            sa.String(length=64),
            sa.ForeignKey("dashboard_snapshot_sets.dashboard_snapshot_set_id"),
            nullable=False,
        ),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dashboard_snapshot_id"),
    )
    op.create_index("ix_dashboard_snapshot_records_set_id", "dashboard_snapshot_records", ["dashboard_snapshot_set_id"])

    op.create_table(
        "dashboard_metric_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "dashboard_snapshot_id",
            sa.String(length=64),
            sa.ForeignKey("dashboard_snapshot_records.dashboard_snapshot_id"),
            nullable=False,
        ),
        sa.Column("metric_code", sa.String(length=64), nullable=False),
        sa.Column("metric_value_numeric", sa.Float(), nullable=True),
        sa.Column("metric_value_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dashboard_metric_records_snapshot_id", "dashboard_metric_records", ["dashboard_snapshot_id"])
    op.create_index("ix_dashboard_metric_records_metric_code", "dashboard_metric_records", ["metric_code"])


def downgrade() -> None:
    op.drop_index("ix_dashboard_metric_records_metric_code", table_name="dashboard_metric_records")
    op.drop_index("ix_dashboard_metric_records_snapshot_id", table_name="dashboard_metric_records")
    op.drop_table("dashboard_metric_records")
    op.drop_index("ix_dashboard_snapshot_records_set_id", table_name="dashboard_snapshot_records")
    op.drop_table("dashboard_snapshot_records")
    op.drop_index("ix_dashboard_snapshot_sets_scope_ref", table_name="dashboard_snapshot_sets")
    op.drop_index("ix_dashboard_snapshot_sets_scope_type", table_name="dashboard_snapshot_sets")
    op.drop_table("dashboard_snapshot_sets")
