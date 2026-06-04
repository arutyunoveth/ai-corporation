from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.tender_import.models import TenderImportEvent, TenderImportPayload, TenderImportRun
from src.modules.tender_import.schemas import CreateTenderImportRunRequest
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity, TenderImportRunStatus
from src.shared.errors import NotFoundError
from src.shared.ids import next_tender_import_event_id, next_tender_import_run_id
from src.shared.validation import compute_payload_hash, require_non_empty


def _get_run(session: Session, tender_import_run_id: str) -> TenderImportRun:
    run = session.scalar(select(TenderImportRun).where(TenderImportRun.tender_import_run_id == tender_import_run_id))
    if not run:
        raise NotFoundError(f"Tender import run '{tender_import_run_id}' was not found")
    return run


def _get_events(session: Session, tender_import_run_id: str) -> list[TenderImportEvent]:
    return list(
        session.scalars(
            select(TenderImportEvent)
            .where(TenderImportEvent.tender_import_run_id == tender_import_run_id)
            .order_by(TenderImportEvent.created_at.asc(), TenderImportEvent.id.asc())
        )
    )


def _get_payload(session: Session, tender_import_event_id: str) -> TenderImportPayload:
    payload = session.scalar(
        select(TenderImportPayload).where(TenderImportPayload.tender_import_event_id == tender_import_event_id)
    )
    if not payload:
        raise NotFoundError(f"Tender import payload for event '{tender_import_event_id}' was not found")
    return payload


def create_tender_import_run(session: Session, payload: CreateTenderImportRunRequest) -> TenderImportRun:
    run = TenderImportRun(
        tender_import_run_id=next_tender_import_run_id(session, TenderImportRun.tender_import_run_id),
        source_type=require_non_empty(payload.source_type, "source_type"),
        source_ref=require_non_empty(payload.source_ref, "source_ref"),
        run_status=TenderImportRunStatus.STARTED,
    )
    session.add(run)
    session.flush()
    append_event_record(
        session,
        deal_id=None,
        event_code="tender_import_run_started",
        source_module_id="M-007",
        severity=EventSeverity.INFO,
        payload_json={"tender_import_run_id": run.tender_import_run_id, "source_type": run.source_type},
    )
    try:
        event_inputs = payload.events or [
            {
                "source_url": payload.source_ref,
                "payload_json": {},
                "raw_procurement_number": None,
            }
        ]
        for item in event_inputs:
            raw_procurement_number = (
                item.raw_procurement_number if hasattr(item, "raw_procurement_number") else item.get("raw_procurement_number")
            )
            source_url = item.source_url if hasattr(item, "source_url") else item.get("source_url")
            payload_json = item.payload_json if hasattr(item, "payload_json") else item.get("payload_json", {})
            event = TenderImportEvent(
                tender_import_event_id=next_tender_import_event_id(session, TenderImportEvent.tender_import_event_id),
                tender_import_run_id=run.tender_import_run_id,
                raw_procurement_number=raw_procurement_number,
                source_url=source_url or payload.source_ref,
            )
            session.add(event)
            session.flush()
            session.add(
                TenderImportPayload(
                    tender_import_event_id=event.tender_import_event_id,
                    payload_json=payload_json,
                    payload_hash=compute_payload_hash(payload_json),
                )
            )
            append_event_record(
                session,
                deal_id=None,
                event_code="tender_import_event_recorded",
                source_module_id="M-007",
                severity=EventSeverity.INFO,
                payload_json={
                    "tender_import_run_id": run.tender_import_run_id,
                    "tender_import_event_id": event.tender_import_event_id,
                    "raw_procurement_number": event.raw_procurement_number,
                },
            )
        run.run_status = TenderImportRunStatus.SUCCEEDED
        run.updated_at = utcnow()
        session.add(run)
        append_event_record(
            session,
            deal_id=None,
            event_code="tender_import_run_succeeded",
            source_module_id="M-007",
            severity=EventSeverity.INFO,
            payload_json={"tender_import_run_id": run.tender_import_run_id},
        )
        session.commit()
        session.refresh(run)
        return run
    except Exception as exc:
        run.run_status = TenderImportRunStatus.FAILED
        run.updated_at = utcnow()
        session.add(run)
        append_event_record(
            session,
            deal_id=None,
            event_code="tender_import_run_failed",
            source_module_id="M-007",
            severity=EventSeverity.HIGH,
            payload_json={"tender_import_run_id": run.tender_import_run_id, "error": str(exc)},
        )
        session.commit()
        raise


def get_tender_import_run(
    session: Session,
    tender_import_run_id: str,
) -> tuple[TenderImportRun, list[tuple[TenderImportEvent, TenderImportPayload]]]:
    run = _get_run(session, tender_import_run_id)
    events = [(event, _get_payload(session, event.tender_import_event_id)) for event in _get_events(session, tender_import_run_id)]
    return run, events


def list_tender_import_events(
    session: Session,
) -> list[tuple[TenderImportEvent, TenderImportPayload]]:
    events = list(
        session.scalars(
            select(TenderImportEvent).order_by(TenderImportEvent.created_at.desc(), TenderImportEvent.id.desc())
        )
    )
    return [(event, _get_payload(session, event.tender_import_event_id)) for event in events]


def get_tender_import_event(
    session: Session,
    tender_import_event_id: str,
) -> tuple[TenderImportEvent, TenderImportPayload]:
    event = session.scalar(
        select(TenderImportEvent).where(TenderImportEvent.tender_import_event_id == tender_import_event_id)
    )
    if not event:
        raise NotFoundError(f"Tender import event '{tender_import_event_id}' was not found")
    return event, _get_payload(session, tender_import_event_id)
