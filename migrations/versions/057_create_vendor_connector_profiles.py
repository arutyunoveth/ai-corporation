"""create vendor connector profile tables"""

from alembic import op
import sqlalchemy as sa

revision = "057_create_vendor_connector_profiles"
down_revision = "056_create_execution_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vendor_connector_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("vendor_connector_set_id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_ref", sa.String(length=128), nullable=False),
        sa.Column("profile_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("vendor_connector_set_id"),
    )
    op.create_index("ix_vendor_connector_sets_scope_type", "vendor_connector_sets", ["scope_type"])
    op.create_index("ix_vendor_connector_sets_scope_ref", "vendor_connector_sets", ["scope_ref"])

    op.create_table(
        "vendor_connector_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("vendor_connector_id", sa.String(length=64), nullable=False),
        sa.Column(
            "vendor_connector_set_id",
            sa.String(length=64),
            sa.ForeignKey("vendor_connector_sets.vendor_connector_set_id"),
            nullable=False,
        ),
        sa.Column("connector_registry_id", sa.String(length=64), nullable=False),
        sa.Column("vendor_code", sa.String(length=64), nullable=False),
        sa.Column("vendor_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("vendor_connector_id"),
    )
    op.create_index("ix_vendor_connector_records_set_id", "vendor_connector_records", ["vendor_connector_set_id"])
    op.create_index(
        "ix_vendor_connector_records_connector_registry_id",
        "vendor_connector_records",
        ["connector_registry_id"],
    )
    op.create_index(
        "ix_vendor_connector_records_vendor_status",
        "vendor_connector_records",
        ["vendor_status"],
    )

    op.create_table(
        "vendor_connector_capabilities",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "vendor_connector_id",
            sa.String(length=64),
            sa.ForeignKey("vendor_connector_records.vendor_connector_id"),
            nullable=False,
        ),
        sa.Column("capability_code", sa.String(length=64), nullable=False),
        sa.Column("capability_status", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_vendor_connector_capabilities_vendor_connector_id",
        "vendor_connector_capabilities",
        ["vendor_connector_id"],
    )
    op.create_index(
        "ix_vendor_connector_capabilities_capability_status",
        "vendor_connector_capabilities",
        ["capability_status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_vendor_connector_capabilities_capability_status",
        table_name="vendor_connector_capabilities",
    )
    op.drop_index(
        "ix_vendor_connector_capabilities_vendor_connector_id",
        table_name="vendor_connector_capabilities",
    )
    op.drop_table("vendor_connector_capabilities")
    op.drop_index("ix_vendor_connector_records_vendor_status", table_name="vendor_connector_records")
    op.drop_index(
        "ix_vendor_connector_records_connector_registry_id",
        table_name="vendor_connector_records",
    )
    op.drop_index("ix_vendor_connector_records_set_id", table_name="vendor_connector_records")
    op.drop_table("vendor_connector_records")
    op.drop_index("ix_vendor_connector_sets_scope_ref", table_name="vendor_connector_sets")
    op.drop_index("ix_vendor_connector_sets_scope_type", table_name="vendor_connector_sets")
    op.drop_table("vendor_connector_sets")
