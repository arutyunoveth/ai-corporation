"""create requirement extraction tables"""

from alembic import op
import sqlalchemy as sa

revision = "064_create_requirement_extraction"
down_revision = "063_create_intake_priority"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "requirement_extraction_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("requirement_extraction_set_id", sa.String(length=64), nullable=False),
        sa.Column(
            "document_set_id",
            sa.String(length=64),
            sa.ForeignKey("document_sets.document_set_id"),
            nullable=False,
        ),
        sa.Column("extraction_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("requirement_extraction_set_id"),
    )
    op.create_index(
        "ix_requirement_extraction_sets_document_set_id",
        "requirement_extraction_sets",
        ["document_set_id"],
    )
    op.create_index(
        "ix_requirement_extraction_sets_status",
        "requirement_extraction_sets",
        ["extraction_status"],
    )

    op.create_table(
        "requirement_extraction_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("requirement_extraction_id", sa.String(length=64), nullable=False),
        sa.Column(
            "requirement_extraction_set_id",
            sa.String(length=64),
            sa.ForeignKey("requirement_extraction_sets.requirement_extraction_set_id"),
            nullable=False,
        ),
        sa.Column("requirement_code", sa.String(length=64), nullable=False),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("requirement_group", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("requirement_extraction_id"),
    )
    op.create_index(
        "ix_requirement_extraction_records_set_id",
        "requirement_extraction_records",
        ["requirement_extraction_set_id"],
    )
    op.create_index(
        "ix_requirement_extraction_records_requirement_code",
        "requirement_extraction_records",
        ["requirement_code"],
    )

    op.create_table(
        "requirement_source_links",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "requirement_extraction_id",
            sa.String(length=64),
            sa.ForeignKey("requirement_extraction_records.requirement_extraction_id"),
            nullable=False,
        ),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_requirement_source_links_requirement_extraction_id",
        "requirement_source_links",
        ["requirement_extraction_id"],
    )
    op.create_index(
        "ix_requirement_source_links_source_ref",
        "requirement_source_links",
        ["source_ref"],
    )


def downgrade() -> None:
    op.drop_index("ix_requirement_source_links_source_ref", table_name="requirement_source_links")
    op.drop_index(
        "ix_requirement_source_links_requirement_extraction_id",
        table_name="requirement_source_links",
    )
    op.drop_table("requirement_source_links")
    op.drop_index(
        "ix_requirement_extraction_records_requirement_code",
        table_name="requirement_extraction_records",
    )
    op.drop_index(
        "ix_requirement_extraction_records_set_id",
        table_name="requirement_extraction_records",
    )
    op.drop_table("requirement_extraction_records")
    op.drop_index(
        "ix_requirement_extraction_sets_status",
        table_name="requirement_extraction_sets",
    )
    op.drop_index(
        "ix_requirement_extraction_sets_document_set_id",
        table_name="requirement_extraction_sets",
    )
    op.drop_table("requirement_extraction_sets")
