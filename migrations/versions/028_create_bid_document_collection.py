"""create bid document collection tables"""

from alembic import op
import sqlalchemy as sa

revision = "028_create_bid_document_collection"
down_revision = "027_create_ceo_approval"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bid_document_collection_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("bid_document_collection_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "document_requirement_set_id",
            sa.String(length=64),
            sa.ForeignKey("document_requirement_sets.document_requirement_set_id"),
            nullable=False,
        ),
        sa.Column(
            "ceo_approval_set_id",
            sa.String(length=64),
            sa.ForeignKey("ceo_approval_sets.ceo_approval_set_id"),
            nullable=False,
        ),
        sa.Column("collection_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("bid_document_collection_set_id"),
    )
    op.create_index("ix_bid_document_collection_sets_deal_id", "bid_document_collection_sets", ["deal_id"])
    op.create_index(
        "ix_bid_document_collection_sets_requirement_set_id",
        "bid_document_collection_sets",
        ["document_requirement_set_id"],
    )

    op.create_table(
        "bid_document_collection_rows",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "bid_document_collection_set_id",
            sa.String(length=64),
            sa.ForeignKey("bid_document_collection_sets.bid_document_collection_set_id"),
            nullable=False,
        ),
        sa.Column("requirement_row_ref", sa.String(length=128), nullable=False),
        sa.Column("artifact_ref", sa.String(length=64), sa.ForeignKey("document_artifacts.artifact_ref"), nullable=True),
        sa.Column("collection_status", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bid_document_collection_rows_set_id", "bid_document_collection_rows", ["bid_document_collection_set_id"])
    op.create_index(
        "ix_bid_document_collection_rows_requirement_row_ref",
        "bid_document_collection_rows",
        ["requirement_row_ref"],
    )
    op.create_index(
        "ix_bid_document_collection_rows_collection_status",
        "bid_document_collection_rows",
        ["collection_status"],
    )

    op.create_table(
        "bid_document_collection_bindings",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "bid_document_collection_set_id",
            sa.String(length=64),
            sa.ForeignKey("bid_document_collection_sets.bid_document_collection_set_id"),
            nullable=False,
        ),
        sa.Column("source_object_type", sa.Text(), nullable=False),
        sa.Column("source_object_ref", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bid_document_collection_bindings_set_id", "bid_document_collection_bindings", ["bid_document_collection_set_id"])
    op.create_index(
        "ix_bid_document_collection_bindings_source_ref",
        "bid_document_collection_bindings",
        ["source_object_type", "source_object_ref"],
    )


def downgrade() -> None:
    op.drop_index("ix_bid_document_collection_bindings_source_ref", table_name="bid_document_collection_bindings")
    op.drop_index("ix_bid_document_collection_bindings_set_id", table_name="bid_document_collection_bindings")
    op.drop_table("bid_document_collection_bindings")
    op.drop_index("ix_bid_document_collection_rows_collection_status", table_name="bid_document_collection_rows")
    op.drop_index("ix_bid_document_collection_rows_requirement_row_ref", table_name="bid_document_collection_rows")
    op.drop_index("ix_bid_document_collection_rows_set_id", table_name="bid_document_collection_rows")
    op.drop_table("bid_document_collection_rows")
    op.drop_index("ix_bid_document_collection_sets_requirement_set_id", table_name="bid_document_collection_sets")
    op.drop_index("ix_bid_document_collection_sets_deal_id", table_name="bid_document_collection_sets")
    op.drop_table("bid_document_collection_sets")
