"""create supplier contract tables

Revision ID: 069_create_supplier_contracts
Revises: 068_create_contract_negotiation
Create Date: 2026-06-04 09:30:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "069_create_supplier_contracts"
down_revision: str | Sequence[str] | None = "068_create_contract_negotiation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "supplier_contract_sets",
        sa.Column("supplier_contract_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), nullable=False),
        sa.Column("supplier_id", sa.String(length=64), nullable=False),
        sa.Column("contract_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.deal_id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["supplier_profiles.supplier_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supplier_contract_set_id"),
    )
    op.create_index("ix_supplier_contract_sets_deal_id", "supplier_contract_sets", ["deal_id"])
    op.create_index("ix_supplier_contract_sets_supplier_id", "supplier_contract_sets", ["supplier_id"])

    op.create_table(
        "supplier_contract_records",
        sa.Column("supplier_contract_id", sa.String(length=64), nullable=False),
        sa.Column("supplier_contract_set_id", sa.String(length=64), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("contract_manifest_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["supplier_contract_set_id"], ["supplier_contract_sets.supplier_contract_set_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supplier_contract_id"),
    )
    op.create_index("ix_supplier_contract_records_set_id", "supplier_contract_records", ["supplier_contract_set_id"])

    op.create_table(
        "supplier_contract_obligations",
        sa.Column("supplier_contract_id", sa.String(length=64), nullable=False),
        sa.Column("obligation_code", sa.String(length=64), nullable=False),
        sa.Column("obligation_text", sa.Text(), nullable=False),
        sa.Column("obligation_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["supplier_contract_id"], ["supplier_contract_records.supplier_contract_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_supplier_contract_obligations_contract_id",
        "supplier_contract_obligations",
        ["supplier_contract_id"],
    )
    op.create_index(
        "ix_supplier_contract_obligations_obligation_code",
        "supplier_contract_obligations",
        ["obligation_code"],
    )

    op.create_table(
        "supplier_contract_comments",
        sa.Column("supplier_contract_id", sa.String(length=64), nullable=False),
        sa.Column("clause_ref", sa.String(length=128), nullable=False),
        sa.Column("comment_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["supplier_contract_id"], ["supplier_contract_records.supplier_contract_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_supplier_contract_comments_contract_id", "supplier_contract_comments", ["supplier_contract_id"])
    op.create_index("ix_supplier_contract_comments_clause_ref", "supplier_contract_comments", ["clause_ref"])


def downgrade() -> None:
    op.drop_index("ix_supplier_contract_comments_clause_ref", table_name="supplier_contract_comments")
    op.drop_index("ix_supplier_contract_comments_contract_id", table_name="supplier_contract_comments")
    op.drop_table("supplier_contract_comments")
    op.drop_index("ix_supplier_contract_obligations_obligation_code", table_name="supplier_contract_obligations")
    op.drop_index("ix_supplier_contract_obligations_contract_id", table_name="supplier_contract_obligations")
    op.drop_table("supplier_contract_obligations")
    op.drop_index("ix_supplier_contract_records_set_id", table_name="supplier_contract_records")
    op.drop_table("supplier_contract_records")
    op.drop_index("ix_supplier_contract_sets_supplier_id", table_name="supplier_contract_sets")
    op.drop_index("ix_supplier_contract_sets_deal_id", table_name="supplier_contract_sets")
    op.drop_table("supplier_contract_sets")
