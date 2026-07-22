"""add R8 current run invariant

Revision ID: 095_add_r8_current_run
Revises: 094_add_r8_canonical_results_and_artifacts
"""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "095_add_r8_current_run"
down_revision: str | Sequence[str] | None = "094_add_r8_canonical_results_and_artifacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    bind = op.get_bind(); inspector = sa.inspect(bind)
    columns = {item["name"] for item in inspector.get_columns("procurement_cases")}
    if "current_run_id" not in columns:
        op.add_column("procurement_cases", sa.Column("current_run_id", sa.String(36), nullable=True))
    if bind.dialect.name == "postgresql":
        names = {item["name"] for item in inspector.get_foreign_keys("procurement_cases")}
        if "fk_procurement_cases_current_run" not in names:
            op.create_foreign_key("fk_procurement_cases_current_run", "procurement_cases", "tender_analysis_runs", ["current_run_id"], ["id"])

def downgrade() -> None:
    pass
