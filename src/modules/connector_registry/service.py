from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.connector_registry.models import ConnectorRegistryRecord, ConnectorRegistrySet, ConnectorSyncRun
from src.modules.connector_registry.schemas import BuildConnectorRegistryRequest, RunConnectorSyncRequest
from src.modules.event_log.service import append_event_record
from src.shared.control_package import ensure_scope_exists, resolve_scope_deal_id
from src.shared.db.base import utcnow
from src.shared.enums import (
    ConnectorRegistryStatus,
    ConnectorScopeType,
    ConnectorStatus,
    ConnectorSyncStatus,
    ConnectorType,
    EventSeverity,
)
from src.shared.errors import NotFoundError
from src.shared.ids import (
    next_connector_registry_id,
    next_connector_registry_set_id,
    next_connector_sync_run_id,
)


def _get_set(session: Session, connector_registry_set_id: str) -> ConnectorRegistrySet:
    record = session.scalar(
        select(ConnectorRegistrySet).where(
            ConnectorRegistrySet.connector_registry_set_id == connector_registry_set_id
        )
    )
    if not record:
        raise NotFoundError(f"Connector registry set '{connector_registry_set_id}' was not found")
    return record


def _get_record(session: Session, connector_registry_id: str) -> ConnectorRegistryRecord:
    record = session.scalar(
        select(ConnectorRegistryRecord).where(
            ConnectorRegistryRecord.connector_registry_id == connector_registry_id
        )
    )
    if not record:
        raise NotFoundError(f"Connector registry record '{connector_registry_id}' was not found")
    return record


def _get_records(session: Session, connector_registry_set_id: str) -> list[ConnectorRegistryRecord]:
    return list(
        session.scalars(
            select(ConnectorRegistryRecord)
            .where(ConnectorRegistryRecord.connector_registry_set_id == connector_registry_set_id)
            .order_by(ConnectorRegistryRecord.created_at.asc(), ConnectorRegistryRecord.id.asc())
        )
    )


def _get_sync_runs(session: Session, connector_registry_id: str) -> list[ConnectorSyncRun]:
    return list(
        session.scalars(
            select(ConnectorSyncRun)
            .where(ConnectorSyncRun.connector_registry_id == connector_registry_id)
            .order_by(ConnectorSyncRun.created_at.asc(), ConnectorSyncRun.id.asc())
        )
    )


def _get_record_with_runs(
    session: Session,
    connector_registry_id: str,
) -> tuple[ConnectorRegistryRecord, list[ConnectorSyncRun]]:
    record = _get_record(session, connector_registry_id)
    return record, _get_sync_runs(session, connector_registry_id)


def _connector_specs(scope_type: ConnectorScopeType) -> list[dict]:
    if scope_type == ConnectorScopeType.GLOBAL:
        return [
            {"connector_code": "GLOBAL_CRM", "connector_type": ConnectorType.CRM, "connector_status": ConnectorStatus.ACTIVE},
            {"connector_code": "GLOBAL_DRIVE", "connector_type": ConnectorType.DRIVE, "connector_status": ConnectorStatus.ACTIVE},
            {"connector_code": "GLOBAL_SHEETS", "connector_type": ConnectorType.SHEETS, "connector_status": ConnectorStatus.ACTIVE},
        ]
    if scope_type == ConnectorScopeType.DEAL:
        return [
            {"connector_code": "DEAL_PORTAL", "connector_type": ConnectorType.PORTAL, "connector_status": ConnectorStatus.ACTIVE},
            {"connector_code": "DEAL_EMAIL", "connector_type": ConnectorType.EMAIL, "connector_status": ConnectorStatus.ACTIVE},
            {"connector_code": "DEAL_DRIVE", "connector_type": ConnectorType.DRIVE, "connector_status": ConnectorStatus.ACTIVE},
        ]
    if scope_type == ConnectorScopeType.PIPELINE:
        return [
            {"connector_code": "PIPELINE_CRM", "connector_type": ConnectorType.CRM, "connector_status": ConnectorStatus.ACTIVE},
            {"connector_code": "PIPELINE_SHEETS", "connector_type": ConnectorType.SHEETS, "connector_status": ConnectorStatus.ACTIVE},
        ]
    return [
        {"connector_code": "EXECUTION_EMAIL", "connector_type": ConnectorType.EMAIL, "connector_status": ConnectorStatus.ACTIVE},
        {"connector_code": "EXECUTION_DRIVE", "connector_type": ConnectorType.DRIVE, "connector_status": ConnectorStatus.ACTIVE},
        {"connector_code": "EXECUTION_SHEETS", "connector_type": ConnectorType.SHEETS, "connector_status": ConnectorStatus.INACTIVE},
    ]


def build_connector_registry(session: Session, payload: BuildConnectorRegistryRequest) -> ConnectorRegistrySet:
    if payload.scope_type in {ConnectorScopeType.DEAL, ConnectorScopeType.EXECUTION}:
        ensure_scope_exists(session, payload.scope_type, payload.scope_ref)
    registry_set = ConnectorRegistrySet(
        connector_registry_set_id=next_connector_registry_set_id(
            session, ConnectorRegistrySet.connector_registry_set_id
        ),
        scope_type=payload.scope_type,
        scope_ref=payload.scope_ref,
        registry_status=ConnectorRegistryStatus.BUILT,
    )
    session.add(registry_set)
    session.flush()
    try:
        specs = _connector_specs(payload.scope_type)
        for spec in specs:
            session.add(
                ConnectorRegistryRecord(
                    connector_registry_id=next_connector_registry_id(
                        session, ConnectorRegistryRecord.connector_registry_id
                    ),
                    connector_registry_set_id=registry_set.connector_registry_set_id,
                    **spec,
                )
            )
            session.flush()
        append_event_record(
            session,
            deal_id=resolve_scope_deal_id(session, payload.scope_type, payload.scope_ref),
            event_code="connector_registry_built",
            source_module_id="M-054",
            severity=EventSeverity.INFO,
            payload_json={
                "connector_registry_set_id": registry_set.connector_registry_set_id,
                "scope_type": payload.scope_type,
                "scope_ref": payload.scope_ref,
                "connector_count": len(specs),
            },
        )
        session.commit()
        session.refresh(registry_set)
        return registry_set
    except Exception:
        session.rollback()
        raise


def run_connector_sync(session: Session, payload: RunConnectorSyncRequest) -> ConnectorSyncRun:
    connector = _get_record(session, payload.connector_registry_id)
    registry_set = _get_set(session, connector.connector_registry_set_id)
    deal_id = resolve_scope_deal_id(session, registry_set.scope_type, registry_set.scope_ref)
    started_at = utcnow()
    append_event_record(
        session,
        deal_id=deal_id,
        event_code="connector_sync_started",
        source_module_id="M-054",
        severity=EventSeverity.INFO,
        payload_json={
            "connector_registry_set_id": registry_set.connector_registry_set_id,
            "connector_registry_id": connector.connector_registry_id,
            "connector_code": connector.connector_code,
        },
    )
    session.flush()
    try:
        if connector.connector_status == ConnectorStatus.DISABLED:
            sync_status = ConnectorSyncStatus.SKIPPED
            sync_summary = payload.sync_summary or "Sync skipped because connector is disabled."
        elif connector.connector_status == ConnectorStatus.INACTIVE:
            sync_status = ConnectorSyncStatus.SKIPPED
            sync_summary = payload.sync_summary or "Sync skipped because connector is inactive."
        else:
            sync_status = ConnectorSyncStatus.SUCCEEDED
            sync_summary = payload.sync_summary or f"Connector {connector.connector_code} synced successfully."
        sync_run = ConnectorSyncRun(
            connector_sync_run_id=next_connector_sync_run_id(session, ConnectorSyncRun.connector_sync_run_id),
            connector_registry_id=connector.connector_registry_id,
            sync_status=sync_status,
            sync_summary=sync_summary,
            started_at=started_at,
            finished_at=utcnow(),
        )
        connector.updated_at = utcnow()
        session.add(sync_run)
        session.flush()
        append_event_record(
            session,
            deal_id=deal_id,
            event_code="connector_sync_finished",
            source_module_id="M-054",
            severity=EventSeverity.INFO,
            payload_json={
                "connector_sync_run_id": sync_run.connector_sync_run_id,
                "connector_registry_id": connector.connector_registry_id,
                "sync_status": sync_status,
            },
        )
        session.commit()
        session.refresh(sync_run)
        return sync_run
    except Exception as exc:
        failed_run = ConnectorSyncRun(
            connector_sync_run_id=next_connector_sync_run_id(session, ConnectorSyncRun.connector_sync_run_id),
            connector_registry_id=connector.connector_registry_id,
            sync_status=ConnectorSyncStatus.FAILED,
            sync_summary=f"Sync failed: {exc}",
            started_at=started_at,
            finished_at=utcnow(),
        )
        session.add(failed_run)
        session.flush()
        append_event_record(
            session,
            deal_id=deal_id,
            event_code="connector_sync_failed",
            source_module_id="M-054",
            severity=EventSeverity.HIGH,
            payload_json={
                "connector_registry_id": connector.connector_registry_id,
                "error": str(exc),
            },
        )
        session.commit()
        raise


def get_connector_registry_set(
    session: Session,
    connector_registry_set_id: str,
) -> tuple[ConnectorRegistrySet, list[tuple[ConnectorRegistryRecord, list[ConnectorSyncRun]]]]:
    registry_set = _get_set(session, connector_registry_set_id)
    records = [
        _get_record_with_runs(session, item.connector_registry_id)
        for item in _get_records(session, connector_registry_set_id)
    ]
    return registry_set, records


def get_connector_registry_record(
    session: Session,
    connector_registry_id: str,
) -> tuple[ConnectorRegistryRecord, list[ConnectorSyncRun]]:
    return _get_record_with_runs(session, connector_registry_id)


def list_connector_registry_sets(
    session: Session,
    *,
    scope_type: ConnectorScopeType | None = None,
    scope_ref: str | None = None,
) -> list[tuple[ConnectorRegistrySet, list[tuple[ConnectorRegistryRecord, list[ConnectorSyncRun]]]]]:
    query = select(ConnectorRegistrySet).order_by(
        ConnectorRegistrySet.created_at.desc(),
        ConnectorRegistrySet.id.desc(),
    )
    if scope_type:
        query = query.where(ConnectorRegistrySet.scope_type == scope_type)
    if scope_ref:
        query = query.where(ConnectorRegistrySet.scope_ref == scope_ref)
    sets = list(session.scalars(query))
    return [get_connector_registry_set(session, item.connector_registry_set_id) for item in sets]
