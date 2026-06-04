"""create tender normalization tables"""

from alembic import op
import sqlalchemy as sa

revision = "062_create_tender_normalization"
down_revision = "061_create_tender_import"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tender_normalization_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tender_normalization_set_id", sa.String(length=64), nullable=False),
        sa.Column(
            "tender_import_event_id",
            sa.String(length=64),
            sa.ForeignKey("tender_import_events.tender_import_event_id"),
            nullable=False,
        ),
        sa.Column("normalization_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tender_normalization_set_id"),
    )
    op.create_index(
        "ix_tender_normalization_sets_import_event_id",
        "tender_normalization_sets",
        ["tender_import_event_id"],
    )
    op.create_index(
        "ix_tender_normalization_sets_status",
        "tender_normalization_sets",
        ["normalization_status"],
    )

    op.create_table(
        "tender_normalization_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tender_normalization_id", sa.String(length=64), nullable=False),
        sa.Column(
            "tender_normalization_set_id",
            sa.String(length=64),
            sa.ForeignKey("tender_normalization_sets.tender_normalization_set_id"),
            nullable=False,
        ),
        sa.Column("normalized_procurement_number", sa.Text(), nullable=True),
        sa.Column("normalized_title", sa.Text(), nullable=False),
        sa.Column("normalized_customer_name", sa.Text(), nullable=False),
        sa.Column("normalized_deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tender_normalization_id"),
    )
    op.create_index(
        "ix_tender_normalization_records_set_id",
        "tender_normalization_records",
        ["tender_normalization_set_id"],
    )
    op.create_index(
        "ix_tender_normalization_records_procurement_number",
        "tender_normalization_records",
        ["normalized_procurement_number"],
    )

    op.create_table(
        "tender_normalization_links",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "tender_normalization_id",
            sa.String(length=64),
            sa.ForeignKey("tender_normalization_records.tender_normalization_id"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.String(length=64),
            sa.ForeignKey("customer_profiles.customer_id"),
            nullable=True,
        ),
        sa.Column(
            "deal_id",
            sa.String(length=32),
            sa.ForeignKey("deals.deal_id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_tender_normalization_links_normalization_id",
        "tender_normalization_links",
        ["tender_normalization_id"],
    )
    op.create_index(
        "ix_tender_normalization_links_customer_id",
        "tender_normalization_links",
        ["customer_id"],
    )
    op.create_index("ix_tender_normalization_links_deal_id", "tender_normalization_links", ["deal_id"])


def downgrade() -> None:
    op.drop_index("ix_tender_normalization_links_deal_id", table_name="tender_normalization_links")
    op.drop_index(
        "ix_tender_normalization_links_customer_id",
        table_name="tender_normalization_links",
    )
    op.drop_index(
        "ix_tender_normalization_links_normalization_id",
        table_name="tender_normalization_links",
    )
    op.drop_table("tender_normalization_links")
    op.drop_index(
        "ix_tender_normalization_records_procurement_number",
        table_name="tender_normalization_records",
    )
    op.drop_index(
        "ix_tender_normalization_records_set_id",
        table_name="tender_normalization_records",
    )
    op.drop_table("tender_normalization_records")
    op.drop_index("ix_tender_normalization_sets_status", table_name="tender_normalization_sets")
    op.drop_index(
        "ix_tender_normalization_sets_import_event_id",
        table_name="tender_normalization_sets",
    )
    op.drop_table("tender_normalization_sets")
