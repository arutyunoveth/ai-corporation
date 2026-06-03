"""create optimization recommendation tables"""

from alembic import op
import sqlalchemy as sa

revision = "049_create_optimization_recommendations"
down_revision = "048_create_workflow_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "optimization_recommendation_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("optimization_recommendation_set_id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_ref", sa.String(length=128), nullable=False),
        sa.Column("optimization_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("optimization_recommendation_set_id"),
    )
    op.create_index(
        "ix_optimization_recommendation_sets_scope_type",
        "optimization_recommendation_sets",
        ["scope_type"],
    )
    op.create_index(
        "ix_optimization_recommendation_sets_scope_ref",
        "optimization_recommendation_sets",
        ["scope_ref"],
    )

    op.create_table(
        "optimization_recommendation_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("optimization_recommendation_id", sa.String(length=64), nullable=False),
        sa.Column(
            "optimization_recommendation_set_id",
            sa.String(length=64),
            sa.ForeignKey("optimization_recommendation_sets.optimization_recommendation_set_id"),
            nullable=False,
        ),
        sa.Column("recommendation_code", sa.String(length=64), nullable=False),
        sa.Column("recommendation_type", sa.Text(), nullable=False),
        sa.Column("recommendation_text", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("optimization_recommendation_id"),
    )
    op.create_index(
        "ix_optimization_recommendation_records_set_id",
        "optimization_recommendation_records",
        ["optimization_recommendation_set_id"],
    )
    op.create_index(
        "ix_optimization_recommendation_records_type",
        "optimization_recommendation_records",
        ["recommendation_type"],
    )

    op.create_table(
        "optimization_signal_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "optimization_recommendation_id",
            sa.String(length=64),
            sa.ForeignKey("optimization_recommendation_records.optimization_recommendation_id"),
            nullable=False,
        ),
        sa.Column("signal_code", sa.String(length=64), nullable=False),
        sa.Column("signal_value_text", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_optimization_signal_records_recommendation_id",
        "optimization_signal_records",
        ["optimization_recommendation_id"],
    )
    op.create_index(
        "ix_optimization_signal_records_signal_code",
        "optimization_signal_records",
        ["signal_code"],
    )


def downgrade() -> None:
    op.drop_index("ix_optimization_signal_records_signal_code", table_name="optimization_signal_records")
    op.drop_index("ix_optimization_signal_records_recommendation_id", table_name="optimization_signal_records")
    op.drop_table("optimization_signal_records")
    op.drop_index(
        "ix_optimization_recommendation_records_type",
        table_name="optimization_recommendation_records",
    )
    op.drop_index(
        "ix_optimization_recommendation_records_set_id",
        table_name="optimization_recommendation_records",
    )
    op.drop_table("optimization_recommendation_records")
    op.drop_index(
        "ix_optimization_recommendation_sets_scope_ref",
        table_name="optimization_recommendation_sets",
    )
    op.drop_index(
        "ix_optimization_recommendation_sets_scope_type",
        table_name="optimization_recommendation_sets",
    )
    op.drop_table("optimization_recommendation_sets")
