"""seed sprint 1 transition rules"""

from datetime import datetime, timezone
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "005_seed_status_transition_rules"
down_revision = "004_create_event_log"
branch_labels = None
depends_on = None


TRANSITIONS = [
    ("NEW", "CANDIDATE"),
    ("CANDIDATE", "DOCS_ANALYSIS"),
    ("CANDIDATE", "REJECTED_EARLY"),
    ("DOCS_ANALYSIS", "SUPPLIER_SOURCING"),
    ("DOCS_ANALYSIS", "REJECTED_EARLY"),
    ("SUPPLIER_SOURCING", "ECONOMICS_REVIEW"),
    ("ECONOMICS_REVIEW", "WAITING_CEO_APPROVAL_TO_BID"),
    ("WAITING_CEO_APPROVAL_TO_BID", "BID_PREPARATION"),
    ("WAITING_CEO_APPROVAL_TO_BID", "DECLINED_TO_BID"),
    ("BID_PREPARATION", "PRE_SUBMISSION"),
    ("PRE_SUBMISSION", "SUBMISSION"),
    ("SUBMISSION", "POST_SUBMISSION"),
    ("POST_SUBMISSION", "OUTCOME_CAPTURE"),
]


def upgrade() -> None:
    table = sa.table(
        "status_transition_rules",
        sa.column("id", sa.String(length=36)),
        sa.column("from_status", sa.Text()),
        sa.column("to_status", sa.Text()),
        sa.column("is_enabled", sa.Boolean()),
        sa.column("transition_type", sa.Text()),
        sa.column("notes", sa.Text()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(timezone.utc)
    op.bulk_insert(
        table,
        [
            {
                "id": str(uuid4()),
                "from_status": from_status,
                "to_status": to_status,
                "is_enabled": True,
                "transition_type": "BOTH",
                "notes": "Seeded from Sprint 1 source-of-truth docs",
                "created_at": now,
                "updated_at": now,
            }
            for from_status, to_status in TRANSITIONS
        ],
    )


def downgrade() -> None:
    conn = op.get_bind()
    for from_status, to_status in TRANSITIONS:
        conn.execute(
            sa.text(
                "DELETE FROM status_transition_rules WHERE from_status = :from_status AND to_status = :to_status"
            ),
            {"from_status": from_status, "to_status": to_status},
        )

