"""create customer registry tables"""

from alembic import op
import sqlalchemy as sa

revision = "060_create_customer_registry"
down_revision = "059_create_external_execution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_profiles",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("customer_id", sa.String(length=64), nullable=False),
        sa.Column("legal_name", sa.Text(), nullable=False),
        sa.Column("inn", sa.String(length=32), nullable=True),
        sa.Column("kpp", sa.String(length=32), nullable=True),
        sa.Column("customer_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("customer_id"),
    )
    op.create_index("ix_customer_profiles_inn", "customer_profiles", ["inn"])
    op.create_index("ix_customer_profiles_legal_name", "customer_profiles", ["legal_name"])
    op.create_index("ix_customer_profiles_customer_status", "customer_profiles", ["customer_status"])

    op.create_table(
        "customer_external_refs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "customer_id",
            sa.String(length=64),
            sa.ForeignKey("customer_profiles.customer_id"),
            nullable=False,
        ),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_customer_external_refs_customer_id", "customer_external_refs", ["customer_id"])
    op.create_index("ix_customer_external_refs_source_type", "customer_external_refs", ["source_type"])

    op.create_table(
        "customer_contours",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "customer_id",
            sa.String(length=64),
            sa.ForeignKey("customer_profiles.customer_id"),
            nullable=False,
        ),
        sa.Column("contour_code", sa.String(length=64), nullable=False),
        sa.Column("contour_name", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_customer_contours_customer_id", "customer_contours", ["customer_id"])
    op.create_index("ix_customer_contours_contour_code", "customer_contours", ["contour_code"])


def downgrade() -> None:
    op.drop_index("ix_customer_contours_contour_code", table_name="customer_contours")
    op.drop_index("ix_customer_contours_customer_id", table_name="customer_contours")
    op.drop_table("customer_contours")
    op.drop_index("ix_customer_external_refs_source_type", table_name="customer_external_refs")
    op.drop_index("ix_customer_external_refs_customer_id", table_name="customer_external_refs")
    op.drop_table("customer_external_refs")
    op.drop_index("ix_customer_profiles_customer_status", table_name="customer_profiles")
    op.drop_index("ix_customer_profiles_legal_name", table_name="customer_profiles")
    op.drop_index("ix_customer_profiles_inn", table_name="customer_profiles")
    op.drop_table("customer_profiles")
