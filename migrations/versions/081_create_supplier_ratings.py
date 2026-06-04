"""create supplier rating update tables

Revision ID: 081_create_supplier_ratings
Revises: 080_create_postmortems
Create Date: 2026-06-04 15:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "081_create_supplier_ratings"
down_revision: str | Sequence[str] | None = "080_create_postmortems"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "supplier_rating_update_sets",
        sa.Column("supplier_rating_update_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), nullable=False),
        sa.Column("supplier_id", sa.String(length=64), nullable=False),
        sa.Column("supplier_contract_set_id", sa.String(length=64), nullable=False),
        sa.Column("postmortem_set_id", sa.String(length=64), nullable=False),
        sa.Column("rating_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.deal_id"]),
        sa.ForeignKeyConstraint(["postmortem_set_id"], ["postmortem_sets.postmortem_set_id"]),
        sa.ForeignKeyConstraint(["supplier_contract_set_id"], ["supplier_contract_sets.supplier_contract_set_id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["supplier_profiles.supplier_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supplier_rating_update_set_id"),
    )
    op.create_index("ix_supplier_rating_update_sets_deal_id", "supplier_rating_update_sets", ["deal_id"])
    op.create_index("ix_supplier_rating_update_sets_supplier_id", "supplier_rating_update_sets", ["supplier_id"])

    op.create_table(
        "supplier_rating_update_records",
        sa.Column("supplier_rating_update_id", sa.String(length=64), nullable=False),
        sa.Column("supplier_rating_update_set_id", sa.String(length=64), nullable=False),
        sa.Column("prior_rating_value", sa.Float(), nullable=True),
        sa.Column("updated_rating_value", sa.Float(), nullable=False),
        sa.Column("rating_band", sa.Text(), nullable=False),
        sa.Column("rationale_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["supplier_rating_update_set_id"], ["supplier_rating_update_sets.supplier_rating_update_set_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supplier_rating_update_id"),
    )
    op.create_index("ix_supplier_rating_update_records_set_id", "supplier_rating_update_records", ["supplier_rating_update_set_id"])

    op.create_table(
        "supplier_rating_factors",
        sa.Column("supplier_rating_update_id", sa.String(length=64), nullable=False),
        sa.Column("factor_code", sa.String(length=64), nullable=False),
        sa.Column("factor_score", sa.Float(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["supplier_rating_update_id"], ["supplier_rating_update_records.supplier_rating_update_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_supplier_rating_factors_update_id", "supplier_rating_factors", ["supplier_rating_update_id"])
    op.create_index("ix_supplier_rating_factors_factor_code", "supplier_rating_factors", ["factor_code"])


def downgrade() -> None:
    op.drop_index("ix_supplier_rating_factors_factor_code", table_name="supplier_rating_factors")
    op.drop_index("ix_supplier_rating_factors_update_id", table_name="supplier_rating_factors")
    op.drop_table("supplier_rating_factors")
    op.drop_index("ix_supplier_rating_update_records_set_id", table_name="supplier_rating_update_records")
    op.drop_table("supplier_rating_update_records")
    op.drop_index("ix_supplier_rating_update_sets_supplier_id", table_name="supplier_rating_update_sets")
    op.drop_index("ix_supplier_rating_update_sets_deal_id", table_name="supplier_rating_update_sets")
    op.drop_table("supplier_rating_update_sets")
