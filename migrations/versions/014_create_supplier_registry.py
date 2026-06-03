"""create supplier registry tables"""

from alembic import op
import sqlalchemy as sa

revision = "014_create_supplier_registry"
down_revision = "013_create_initial_tech_risks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplier_profiles",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("supplier_id", sa.String(length=64), nullable=False),
        sa.Column("legal_name", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("inn", sa.String(length=32), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("supplier_id"),
        sa.UniqueConstraint("inn"),
    )
    op.create_index("ix_supplier_profiles_status", "supplier_profiles", ["status"])
    op.create_index("ix_supplier_profiles_legal_name", "supplier_profiles", ["legal_name"])
    op.create_index("ix_supplier_profiles_display_name", "supplier_profiles", ["display_name"])

    op.create_table(
        "supplier_external_refs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("supplier_id", sa.String(length=64), sa.ForeignKey("supplier_profiles.supplier_id"), nullable=False),
        sa.Column("ref_type", sa.String(length=64), nullable=False),
        sa.Column("ref_value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_supplier_external_refs_supplier_id", "supplier_external_refs", ["supplier_id"])
    op.create_index("ix_supplier_external_refs_ref_type", "supplier_external_refs", ["ref_type"])

    op.create_table(
        "supplier_contacts",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("supplier_id", sa.String(length=64), sa.ForeignKey("supplier_profiles.supplier_id"), nullable=False),
        sa.Column("contact_name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_supplier_contacts_supplier_id", "supplier_contacts", ["supplier_id"])
    op.create_index("ix_supplier_contacts_email", "supplier_contacts", ["email"])

    op.create_table(
        "supplier_tags",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("supplier_id", sa.String(length=64), sa.ForeignKey("supplier_profiles.supplier_id"), nullable=False),
        sa.Column("tag_code", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_supplier_tags_supplier_id", "supplier_tags", ["supplier_id"])
    op.create_index("ix_supplier_tags_tag_code", "supplier_tags", ["tag_code"])


def downgrade() -> None:
    op.drop_index("ix_supplier_tags_tag_code", table_name="supplier_tags")
    op.drop_index("ix_supplier_tags_supplier_id", table_name="supplier_tags")
    op.drop_table("supplier_tags")
    op.drop_index("ix_supplier_contacts_email", table_name="supplier_contacts")
    op.drop_index("ix_supplier_contacts_supplier_id", table_name="supplier_contacts")
    op.drop_table("supplier_contacts")
    op.drop_index("ix_supplier_external_refs_ref_type", table_name="supplier_external_refs")
    op.drop_index("ix_supplier_external_refs_supplier_id", table_name="supplier_external_refs")
    op.drop_table("supplier_external_refs")
    op.drop_index("ix_supplier_profiles_display_name", table_name="supplier_profiles")
    op.drop_index("ix_supplier_profiles_legal_name", table_name="supplier_profiles")
    op.drop_index("ix_supplier_profiles_status", table_name="supplier_profiles")
    op.drop_table("supplier_profiles")
