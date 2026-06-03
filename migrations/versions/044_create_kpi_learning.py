"""create kpi learning tables"""

from alembic import op
import sqlalchemy as sa

revision = "044_create_kpi_learning"
down_revision = "043_create_deal_closure"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kpi_learning_sets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("kpi_learning_set_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=32), sa.ForeignKey("deals.deal_id"), nullable=False),
        sa.Column(
            "deal_closure_set_id",
            sa.String(length=64),
            sa.ForeignKey("deal_closure_sets.deal_closure_set_id"),
            nullable=False,
        ),
        sa.Column("kpi_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("kpi_learning_set_id"),
    )
    op.create_index("ix_kpi_learning_sets_deal_id", "kpi_learning_sets", ["deal_id"])
    op.create_index("ix_kpi_learning_sets_deal_closure_set_id", "kpi_learning_sets", ["deal_closure_set_id"])

    op.create_table(
        "kpi_learning_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("kpi_learning_id", sa.String(length=64), nullable=False),
        sa.Column(
            "kpi_learning_set_id",
            sa.String(length=64),
            sa.ForeignKey("kpi_learning_sets.kpi_learning_set_id"),
            nullable=False,
        ),
        sa.Column("cycle_time_days", sa.Float(), nullable=True),
        sa.Column("margin_estimate", sa.Float(), nullable=True),
        sa.Column("supplier_count", sa.Integer(), nullable=False),
        sa.Column("incident_count", sa.Integer(), nullable=False),
        sa.Column("payment_collection_days", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("kpi_learning_id"),
    )
    op.create_index("ix_kpi_learning_records_set_id", "kpi_learning_records", ["kpi_learning_set_id"])

    op.create_table(
        "learning_note_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("learning_note_id", sa.String(length=64), nullable=False),
        sa.Column(
            "kpi_learning_id",
            sa.String(length=64),
            sa.ForeignKey("kpi_learning_records.kpi_learning_id"),
            nullable=False,
        ),
        sa.Column("note_type", sa.Text(), nullable=False),
        sa.Column("note_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("learning_note_id"),
    )
    op.create_index("ix_learning_note_records_kpi_learning_id", "learning_note_records", ["kpi_learning_id"])
    op.create_index("ix_learning_note_records_note_type", "learning_note_records", ["note_type"])


def downgrade() -> None:
    op.drop_index("ix_learning_note_records_note_type", table_name="learning_note_records")
    op.drop_index("ix_learning_note_records_kpi_learning_id", table_name="learning_note_records")
    op.drop_table("learning_note_records")
    op.drop_index("ix_kpi_learning_records_set_id", table_name="kpi_learning_records")
    op.drop_table("kpi_learning_records")
    op.drop_index("ix_kpi_learning_sets_deal_closure_set_id", table_name="kpi_learning_sets")
    op.drop_index("ix_kpi_learning_sets_deal_id", table_name="kpi_learning_sets")
    op.drop_table("kpi_learning_sets")
