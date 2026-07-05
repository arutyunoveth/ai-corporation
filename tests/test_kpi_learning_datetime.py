from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.modules.kpi_learning.models import KPILearningRecord
from src.modules.kpi_learning.schemas import BuildKPILearningRequest
from src.modules.kpi_learning.service import _ensure_aware_utc, build_kpi_learning


def test_ensure_aware_utc_treats_naive_datetimes_as_utc() -> None:
    value = datetime(2026, 7, 5, 12, 30, 0)

    normalized = _ensure_aware_utc(value)

    assert normalized.tzinfo == timezone.utc
    assert normalized == datetime(2026, 7, 5, 12, 30, 0, tzinfo=timezone.utc)


def test_ensure_aware_utc_converts_other_timezones_to_utc() -> None:
    plus_three = timezone(timedelta(hours=3))
    value = datetime(2026, 7, 5, 15, 30, 0, tzinfo=plus_three)

    normalized = _ensure_aware_utc(value)

    assert normalized.tzinfo == timezone.utc
    assert normalized == datetime(2026, 7, 5, 12, 30, 0, tzinfo=timezone.utc)


def test_build_kpi_learning_handles_mixed_datetime_kinds() -> None:
    session = MagicMock()
    session.scalar.side_effect = [
        SimpleNamespace(deal_id="DL-2026-000001", created_at=datetime(2026, 7, 1, 9, 0, 0)),
        0,
    ]

    closure_set = SimpleNamespace(
        deal_id="DL-2026-000001",
        deal_closure_set_id="DCS-2026-000001",
        outcome_intake_set_id="OIS-2026-000001",
        execution_command_set_id="ECS-2026-000001",
        closure_status="CLOSED",
    )
    closure_record = SimpleNamespace(closed_at=datetime(2026, 7, 3, 9, 0, 0, tzinfo=timezone.utc))
    package = SimpleNamespace(
        latest_cost_model_record=None,
        latest_payment_collection_record=None,
        latest_payment_collection_set=None,
        latest_cost_model_set=None,
        incident_count=0,
    )
    payload = BuildKPILearningRequest(
        deal_id="DL-2026-000001",
        deal_closure_set_id="DCS-2026-000001",
        learning_notes=[],
    )

    added_records: list[object] = []

    def capture_add(value: object) -> None:
        added_records.append(value)

    session.add.side_effect = capture_add

    with (
        patch("src.modules.kpi_learning.service.get_deal_closure_set", return_value=(closure_set, [closure_record], [])),
        patch("src.modules.kpi_learning.service.load_closure_package", return_value=package),
        patch("src.modules.kpi_learning.service.next_kpi_learning_set_id", return_value="KLS-2026-000001"),
        patch("src.modules.kpi_learning.service.next_kpi_learning_id", return_value="KLR-2026-000001"),
        patch("src.modules.kpi_learning.service.append_event_record"),
    ):
        result = build_kpi_learning(session, payload)

    kpi_record = next(item for item in added_records if isinstance(item, KPILearningRecord))
    assert result.kpi_learning_set_id == "KLS-2026-000001"
    assert kpi_record.cycle_time_days == 2.0
    assert kpi_record.payment_collection_days is None
    session.commit.assert_called_once()
    session.rollback.assert_not_called()
