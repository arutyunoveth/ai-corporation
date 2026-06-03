"""create learning automation tables"""

from alembic import op
import sqlalchemy as sa

revision = "047_create_learning_automation"
down_revision = "046_create_archive_export"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_automation_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("learning_automation_set_id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_ref", sa.String(length=128), nullable=False),
        sa.Column("automation_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("learning_automation_set_id"),
    )
    op.create_index("ix_learning_automation_sets_scope_type", "learning_automation_sets", ["scope_type"])
    op.create_index("ix_learning_automation_sets_scope_ref", "learning_automation_sets", ["scope_ref"])

    op.create_table(
        "learning_automation_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("learning_automation_id", sa.String(length=64), nullable=False),
        sa.Column(
            "learning_automation_set_id",
            sa.String(length=64),
            sa.ForeignKey("learning_automation_sets.learning_automation_set_id"),
            nullable=False,
        ),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("learning_automation_id"),
    )
    op.create_index("ix_learning_automation_records_set_id", "learning_automation_records", ["learning_automation_set_id"])

    op.create_table(
        "learning_recommendation_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "learning_automation_id",
            sa.String(length=64),
            sa.ForeignKey("learning_automation_records.learning_automation_id"),
            nullable=False,
        ),
        sa.Column("recommendation_code", sa.String(length=64), nullable=False),
        sa.Column("recommendation_type", sa.Text(), nullable=False),
        sa.Column("recommendation_text", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_learning_recommendation_records_automation_id",
        "learning_recommendation_records",
        ["learning_automation_id"],
    )
    op.create_index(
        "ix_learning_recommendation_records_type",
        "learning_recommendation_records",
        ["recommendation_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_learning_recommendation_records_type", table_name="learning_recommendation_records")
    op.drop_index(
        "ix_learning_recommendation_records_automation_id",
        table_name="learning_recommendation_records",
    )
    op.drop_table("learning_recommendation_records")
    op.drop_index("ix_learning_automation_records_set_id", table_name="learning_automation_records")
    op.drop_table("learning_automation_records")
    op.drop_index("ix_learning_automation_sets_scope_ref", table_name="learning_automation_sets")
    op.drop_index("ix_learning_automation_sets_scope_type", table_name="learning_automation_sets")
    op.drop_table("learning_automation_sets")
