"""enable pgvector and add tender research rag tables

Revision ID: 090_enable_pgvector_and_add_rag_tables
Revises: 089_add_document_identity_fields
Create Date: 2026-07-04 23:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "090_enable_pgvector_and_add_rag_tables"
down_revision: str | Sequence[str] | None = "089_add_document_identity_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    if not inspector.has_table("procurement_document_chunks"):
        op.create_table(
            "procurement_document_chunks",
            sa.Column("id", sa.String(36), primary_key=True, nullable=False),
            sa.Column("tender_id", sa.String(36), sa.ForeignKey("procurement_tenders.id"), nullable=False),
            sa.Column("document_id", sa.String(36), sa.ForeignKey("procurement_tender_documents.id"), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("text_hash", sa.String(64), nullable=False),
            sa.Column("char_start", sa.Integer(), nullable=False),
            sa.Column("char_end", sa.Integer(), nullable=False),
            sa.Column("token_estimate", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("source_file_name", sa.String(1024), nullable=True),
            sa.Column("source_text_path", sa.Text(), nullable=True),
            sa.Column("raw_meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("document_id", "chunk_index"),
            sa.UniqueConstraint("document_id", "text_hash"),
        )

    chunk_indexes = {item["name"] for item in inspector.get_indexes("procurement_document_chunks")} if inspector.has_table("procurement_document_chunks") else set()
    if "ix_procurement_document_chunks_tender_id" not in chunk_indexes:
        op.create_index("ix_procurement_document_chunks_tender_id", "procurement_document_chunks", ["tender_id"])
    if "ix_procurement_document_chunks_document_id" not in chunk_indexes:
        op.create_index("ix_procurement_document_chunks_document_id", "procurement_document_chunks", ["document_id"])
    if "ix_procurement_document_chunks_text_hash" not in chunk_indexes:
        op.create_index("ix_procurement_document_chunks_text_hash", "procurement_document_chunks", ["text_hash"])

    if not inspector.has_table("procurement_document_embeddings"):
        op.create_table(
            "procurement_document_embeddings",
            sa.Column("id", sa.String(36), primary_key=True, nullable=False),
            sa.Column("chunk_id", sa.String(36), sa.ForeignKey("procurement_document_chunks.id"), nullable=False),
            sa.Column("provider", sa.String(64), nullable=False),
            sa.Column("model", sa.String(256), nullable=False),
            sa.Column("dimension", sa.Integer(), nullable=False),
            sa.Column("vector_id", sa.String(256), nullable=True),
            sa.Column("embedding_path", sa.Text(), nullable=True),
            sa.Column("embedding_hash", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("chunk_id", "provider", "model"),
        )

    emb_indexes = {item["name"] for item in inspector.get_indexes("procurement_document_embeddings")} if inspector.has_table("procurement_document_embeddings") else set()
    if "ix_procurement_document_embeddings_chunk_id" not in emb_indexes:
        op.create_index("ix_procurement_document_embeddings_chunk_id", "procurement_document_embeddings", ["chunk_id"])
    if "ix_procurement_document_embeddings_vector_id" not in emb_indexes:
        op.create_index("ix_procurement_document_embeddings_vector_id", "procurement_document_embeddings", ["vector_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("procurement_document_embeddings"):
        op.drop_index("ix_procurement_document_embeddings_vector_id", table_name="procurement_document_embeddings")
        op.drop_index("ix_procurement_document_embeddings_chunk_id", table_name="procurement_document_embeddings")
        op.drop_table("procurement_document_embeddings")

    if inspector.has_table("procurement_document_chunks"):
        op.drop_index("ix_procurement_document_chunks_text_hash", table_name="procurement_document_chunks")
        op.drop_index("ix_procurement_document_chunks_document_id", table_name="procurement_document_chunks")
        op.drop_index("ix_procurement_document_chunks_tender_id", table_name="procurement_document_chunks")
        op.drop_table("procurement_document_chunks")
