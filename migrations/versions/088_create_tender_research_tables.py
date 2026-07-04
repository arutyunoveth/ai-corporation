"""create tender research tables

Revision ID: 088_create_tender_research_tables
Revises: 087_add_company_agent_metadata_fields
Create Date: 2026-07-04 12:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "088_create_tender_research_tables"
down_revision: str | Sequence[str] | None = "087_add_company_agent_metadata_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── procurement_tenders ──
    op.create_table(
        "procurement_tenders",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("source", sa.String(64), nullable=False, server_default="eis"),
        sa.Column("external_id", sa.String(256), nullable=False),
        sa.Column("registry_number", sa.String(256), nullable=True),
        sa.Column("purchase_number", sa.String(256), nullable=True),
        sa.Column("law_type", sa.String(32), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("customer_name", sa.String(512), nullable=True),
        sa.Column("customer_inn", sa.String(32), nullable=True),
        sa.Column("customer_kpp", sa.String(32), nullable=True),
        sa.Column("region", sa.String(256), nullable=True),
        sa.Column("platform_name", sa.String(256), nullable=True),
        sa.Column("platform_url", sa.Text(), nullable=True),
        sa.Column("eis_url", sa.Text(), nullable=True),
        sa.Column("nmck_amount", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(16), nullable=True),
        sa.Column("publication_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("application_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auction_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(64), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source", "external_id"),
    )
    op.create_index("ix_procurement_tenders_registry_number", "procurement_tenders", ["registry_number"])
    op.create_index("ix_procurement_tenders_customer_inn", "procurement_tenders", ["customer_inn"])
    op.create_index("ix_procurement_tenders_publication_date", "procurement_tenders", ["publication_date"])
    op.create_index("ix_procurement_tenders_application_deadline", "procurement_tenders", ["application_deadline"])
    op.create_index("ix_procurement_tenders_content_hash", "procurement_tenders", ["content_hash"])

    # ── procurement_customers ──
    op.create_table(
        "procurement_customers",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("inn", sa.String(32), nullable=True),
        sa.Column("kpp", sa.String(32), nullable=True),
        sa.Column("region", sa.String(256), nullable=True),
        sa.Column("normalized_name", sa.String(512), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenders_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_last_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("inn", "kpp"),
    )
    op.create_index("ix_procurement_customers_normalized_name", "procurement_customers", ["normalized_name"])

    # ── procurement_tender_documents ──
    op.create_table(
        "procurement_tender_documents",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("tender_id", sa.String(36), sa.ForeignKey("procurement_tenders.id"), nullable=False),
        sa.Column("source_document_id", sa.String(256), nullable=True),
        sa.Column("file_name", sa.String(1024), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("local_path", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(256), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("download_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("text_extraction_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("extracted_text_path", sa.Text(), nullable=True),
        sa.Column("extracted_text_chars", sa.Integer(), nullable=True),
        sa.Column("raw_meta", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tender_id", "sha256"),
    )
    op.create_index("ix_procurement_tender_documents_tender_id", "procurement_tender_documents", ["tender_id"])
    op.create_index("ix_procurement_tender_documents_download_status", "procurement_tender_documents", ["download_status"])
    op.create_index("ix_procurement_tender_documents_text_extraction_status", "procurement_tender_documents", ["text_extraction_status"])

    # ── procurement_tender_search_queries ──
    op.create_table(
        "procurement_tender_search_queries",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("tender_id", sa.String(36), sa.ForeignKey("procurement_tenders.id"), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("query_type", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("results_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tender_id", "provider", "query"),
    )
    op.create_index("ix_procurement_tender_search_queries_tender_id", "procurement_tender_search_queries", ["tender_id"])
    op.create_index("ix_procurement_tender_search_queries_provider", "procurement_tender_search_queries", ["provider"])
    op.create_index("ix_procurement_tender_search_queries_query_type", "procurement_tender_search_queries", ["query_type"])

    # ── procurement_web_search_results ──
    op.create_table(
        "procurement_web_search_results",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("tender_id", sa.String(36), sa.ForeignKey("procurement_tenders.id"), nullable=False),
        sa.Column("query_id", sa.String(36), sa.ForeignKey("procurement_tender_search_queries.id"), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("normalized_url", sa.Text(), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column("display_url", sa.Text(), nullable=True),
        sa.Column("raw_result", sa.JSON(), nullable=True),
        sa.Column("url_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("query_id", "url_hash"),
    )
    op.create_index("ix_procurement_web_search_results_tender_id", "procurement_web_search_results", ["tender_id"])
    op.create_index("ix_procurement_web_search_results_normalized_url", "procurement_web_search_results", ["normalized_url"])
    op.create_index("ix_procurement_web_search_results_url_hash", "procurement_web_search_results", ["url_hash"])

    # ── procurement_web_pages ──
    op.create_table(
        "procurement_web_pages",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("tender_id", sa.String(36), sa.ForeignKey("procurement_tenders.id"), nullable=True),
        sa.Column("search_result_id", sa.String(36), sa.ForeignKey("procurement_web_search_results.id"), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("normalized_url", sa.Text(), nullable=False),
        sa.Column("url_hash", sa.String(64), nullable=False),
        sa.Column("fetcher", sa.String(32), nullable=False, server_default="requests"),
        sa.Column("fetch_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("content_type", sa.String(256), nullable=True),
        sa.Column("final_url", sa.Text(), nullable=True),
        sa.Column("html_path", sa.Text(), nullable=True),
        sa.Column("text_path", sa.Text(), nullable=True),
        sa.Column("extracted_title", sa.Text(), nullable=True),
        sa.Column("extracted_text_chars", sa.Integer(), nullable=True),
        sa.Column("raw_meta", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("url_hash"),
    )
    op.create_index("ix_procurement_web_pages_tender_id", "procurement_web_pages", ["tender_id"])
    op.create_index("ix_procurement_web_pages_fetch_status", "procurement_web_pages", ["fetch_status"])
    op.create_index("ix_procurement_web_pages_content_type", "procurement_web_pages", ["content_type"])

    # ── procurement_raw_artifacts ──
    op.create_table(
        "procurement_raw_artifacts",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("tender_id", sa.String(36), sa.ForeignKey("procurement_tenders.id"), nullable=True),
        sa.Column("artifact_type", sa.String(64), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("local_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(256), nullable=True),
        sa.Column("raw_meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("sha256"),
    )
    op.create_index("ix_procurement_raw_artifacts_tender_id", "procurement_raw_artifacts", ["tender_id"])
    op.create_index("ix_procurement_raw_artifacts_artifact_type", "procurement_raw_artifacts", ["artifact_type"])


def downgrade() -> None:
    op.drop_table("procurement_raw_artifacts")
    op.drop_table("procurement_web_pages")
    op.drop_table("procurement_web_search_results")
    op.drop_table("procurement_tender_search_queries")
    op.drop_table("procurement_tender_documents")
    op.drop_table("procurement_customers")
    op.drop_table("procurement_tenders")
