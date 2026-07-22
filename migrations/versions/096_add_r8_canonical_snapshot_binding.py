"""add R8 verified immutable canonical snapshot binding

Revision ID: 096_add_r8_canonical_snapshot_binding
Revises: 095_add_r8_current_run
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "096_add_r8_canonical_snapshot_binding"
down_revision: str | Sequence[str] | None = "095_add_r8_current_run"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {item["name"] for item in inspector.get_columns("pilot_run_results")}
    additions = (
        ("requirements_storage_key", sa.Text()),
        ("requirements_file_sha256", sa.String(length=64)),
        ("canonical_report_file_sha256", sa.String(length=64)),
        ("binding_manifest_storage_key", sa.Text()),
        ("binding_manifest_file_sha256", sa.String(length=64)),
        ("source_graph_hash_algorithm", sa.String(length=64)),
        ("report_model_hash", sa.String(length=64)),
        ("verification_policy_version", sa.String(length=64)),
    )
    for name, type_ in additions:
        if name not in columns:
            op.add_column("pilot_run_results", sa.Column(name, type_, nullable=True))
    indexes = {item["name"] for item in inspector.get_indexes("pilot_run_results")}
    for name, columns_ in (
        ("ix_pilot_run_results_binding_manifest_key", ["binding_manifest_storage_key"]),
        ("ix_pilot_run_results_report_model_hash", ["report_model_hash"]),
        ("ix_pilot_run_results_source_graph_hash", ["source_graph_hash"]),
    ):
        if name not in indexes:
            op.create_index(name, "pilot_run_results", columns_)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {item["name"] for item in inspector.get_indexes("pilot_run_results")}
    for name in (
        "ix_pilot_run_results_source_graph_hash",
        "ix_pilot_run_results_report_model_hash",
        "ix_pilot_run_results_binding_manifest_key",
    ):
        if name in indexes:
            op.drop_index(name, table_name="pilot_run_results")
    columns = {item["name"] for item in inspector.get_columns("pilot_run_results")}
    for name in (
        "verification_policy_version", "report_model_hash", "source_graph_hash_algorithm",
        "binding_manifest_file_sha256", "binding_manifest_storage_key",
        "canonical_report_file_sha256", "requirements_file_sha256", "requirements_storage_key",
    ):
        if name in columns:
            op.drop_column("pilot_run_results", name)
