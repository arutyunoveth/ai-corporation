"""create document store tables"""

from alembic import op
import sqlalchemy as sa

revision = "003_create_document_store"
down_revision = "002_create_status_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_artifacts",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("artifact_ref", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=True),
        sa.Column("artifact_type", sa.Text(), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=True),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("checksum_sha256", sa.Text(), nullable=True),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("artifact_ref"),
    )
    op.create_index("ix_document_artifacts_deal_id", "document_artifacts", ["deal_id"])
    op.create_index("ix_document_artifacts_artifact_type", "document_artifacts", ["artifact_type"])

    op.create_table(
        "artifact_versions",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("artifact_ref", sa.String(length=64), sa.ForeignKey("document_artifacts.artifact_ref"), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("checksum_sha256", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("artifact_ref", "version_no", name="uq_artifact_versions_ref_version"),
    )

    op.create_table(
        "artifact_links",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("artifact_ref", sa.String(length=64), sa.ForeignKey("document_artifacts.artifact_ref"), nullable=False),
        sa.Column("linked_object_type", sa.Text(), nullable=False),
        sa.Column("linked_object_ref", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_artifact_links_artifact_ref", "artifact_links", ["artifact_ref"])
    op.create_index("ix_artifact_links_object_ref", "artifact_links", ["linked_object_type", "linked_object_ref"])


def downgrade() -> None:
    op.drop_index("ix_artifact_links_object_ref", table_name="artifact_links")
    op.drop_index("ix_artifact_links_artifact_ref", table_name="artifact_links")
    op.drop_table("artifact_links")
    op.drop_table("artifact_versions")
    op.drop_index("ix_document_artifacts_artifact_type", table_name="document_artifacts")
    op.drop_index("ix_document_artifacts_deal_id", table_name="document_artifacts")
    op.drop_table("document_artifacts")

