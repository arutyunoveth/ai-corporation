from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


EVENTS_FILE = "events.jsonl"

EVENT_STEP_BY_TYPE = {
    "eis_getdocs_started": "Документация",
    "eis_archive_url_received": "Документация",
    "eis_archive_download_started": "Документация",
    "eis_archive_downloaded": "Документация",
    "eis_archive_not_ready": "Документация",
    "eis_archive_extracted": "Документация",
    "run_created_from_eis_archive": "Документация",
    "analysis_ready": "Документация",
    "procurement_search_started": "Поиск закупки",
    "procurement_search_completed": "Поиск закупки",
    "procurement_search_failed": "Поиск закупки",
    "procurement_selected": "Поиск закупки",
    "procurement_details_loaded": "Поиск закупки",
    "attachments_list_loaded": "Документация",
    "attachments_download_started": "Документация",
    "attachment_saved": "Документация",
    "attachment_skipped": "Документация",
    "attachments_download_completed": "Документация",
    "manual_upload_required": "Документация",
    "manual_upload_received": "Документация",
    "run_created_from_procurement": "Документация",
    "uploaded_run_created": "Документация",
    "analysis_started": "Анализ",
    "analysis_completed": "Решение",
    "analysis_blocked": "Анализ",
}

WARNING_EVENTS = {
    "attachment_skipped",
    "manual_upload_required",
    "analysis_blocked",
    "eis_archive_not_ready",
}


def append_tender_demo_event(
    run_id: str,
    event_type: str,
    message_ru: str,
    metadata: dict[str, Any] | None = None,
    *,
    severity: str | None = None,
    step: str | None = None,
) -> dict[str, Any]:
    timestamp = datetime.now(UTC).isoformat()
    payload = _normalize_event(
        {
            "event_type": event_type,
            "timestamp": timestamp,
            "message_ru": message_ru,
            "step": step or EVENT_STEP_BY_TYPE.get(event_type, "Система"),
            "severity": severity or ("warning" if event_type in WARNING_EVENTS else "info"),
            "metadata": metadata or {},
            "created_at": timestamp,
            "message": message_ru,
            "details": metadata or {},
        }
    )
    path = _events_path(run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return payload


def load_tender_demo_events(run_id: str) -> list[dict[str, Any]]:
    path = _events_path(run_id)
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(_normalize_event(json.loads(line)))
    return events


def _normalize_event(payload: dict[str, Any]) -> dict[str, Any]:
    timestamp = payload.get("timestamp") or payload.get("created_at") or datetime.now(UTC).isoformat()
    message_ru = payload.get("message_ru") or payload.get("message") or ""
    metadata = payload.get("metadata") or payload.get("details") or {}
    event_type = payload.get("event_type") or "unknown_event"
    severity = payload.get("severity") or ("warning" if event_type in WARNING_EVENTS else "info")
    if severity not in {"info", "warning", "error"}:
        severity = "info"
    return {
        "event_type": event_type,
        "timestamp": timestamp,
        "message_ru": message_ru,
        "step": payload.get("step") or EVENT_STEP_BY_TYPE.get(event_type, "Система"),
        "severity": severity,
        "metadata": metadata,
        "created_at": payload.get("created_at") or timestamp,
        "message": payload.get("message") or message_ru,
        "details": payload.get("details") or metadata,
    }


def _events_path(run_id: str) -> Path:
    return _runs_root() / run_id / EVENTS_FILE


def _runs_root() -> Path:
    configured = os.environ.get("AI_CORP_TENDER_OPERATOR_DEMO_RUNS_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[3] / "company_agent_runs" / "tender_operator_demo"
