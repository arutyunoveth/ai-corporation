"""add document_identity_hash and document_identity_source to procurement_tender_documents

Revision ID: 089_add_document_identity_fields
Revises: 088_create_tender_research_tables
Create Date: 2026-07-04 17:30:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "089_add_document_identity_fields"
down_revision: str | Sequence[str] | None = "088_create_tender_research_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "procurement_tender_documents",
        sa.Column("document_identity_hash", sa.String(64), nullable=True),
    )
    op.add_column(
        "procurement_tender_documents",
        sa.Column("document_identity_source", sa.String(32), nullable=True),
    )
    op.create_index(
        "ix_procurement_tender_documents_identity_hash",
        "procurement_tender_documents",
        ["tender_id", "document_identity_hash"],
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_procurement_tender_documents_doc_identity "
        "ON procurement_tender_documents(tender_id, document_identity_hash) "
        "WHERE document_identity_hash IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_procurement_tender_documents_doc_identity")
    op.drop_index("ix_procurement_tender_documents_identity_hash", table_name="procurement_tender_documents")
    op.drop_column("procurement_tender_documents", "document_identity_source")
    op.drop_column("procurement_tender_documents", "document_identity_hash")
