from fastapi import APIRouter, Query, status

from src.modules.connector_registry.schemas import (
    BuildConnectorRegistryRequest,
    ConnectorRegistryRecordResponse,
    ConnectorRegistrySetResponse,
    ConnectorSyncRunResponse,
    RunConnectorSyncRequest,
)
from src.modules.connector_registry.service import (
    build_connector_registry,
    get_connector_registry_record,
    get_connector_registry_set,
    list_connector_registry_sets,
    run_connector_sync,
)
from src.shared.api.dependencies import DBSession
from src.shared.enums import ConnectorScopeType

router = APIRouter(tags=["connectors"])


def _to_sync_run_response(item) -> ConnectorSyncRunResponse:
    return ConnectorSyncRunResponse.model_validate(item)


def _to_record_response(result: tuple) -> ConnectorRegistryRecordResponse:
    record, sync_runs = result
    return ConnectorRegistryRecordResponse(
        connector_registry_id=record.connector_registry_id,
        connector_registry_set_id=record.connector_registry_set_id,
        connector_code=record.connector_code,
        connector_type=record.connector_type,
        connector_status=record.connector_status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        sync_runs=[_to_sync_run_response(item) for item in sync_runs],
    )


def _to_set_response(result: tuple) -> ConnectorRegistrySetResponse:
    registry_set, records = result
    return ConnectorRegistrySetResponse(
        connector_registry_set_id=registry_set.connector_registry_set_id,
        scope_type=registry_set.scope_type,
        scope_ref=registry_set.scope_ref,
        registry_status=registry_set.registry_status,
        created_at=registry_set.created_at,
        updated_at=registry_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/connectors/build", response_model=ConnectorRegistrySetResponse, status_code=status.HTTP_201_CREATED)
def build_connector_registry_route(
    payload: BuildConnectorRegistryRequest,
    session: DBSession,
) -> ConnectorRegistrySetResponse:
    registry_set = build_connector_registry(session, payload)
    return _to_set_response(get_connector_registry_set(session, registry_set.connector_registry_set_id))


@router.post("/connectors/sync", response_model=ConnectorRegistryRecordResponse, status_code=status.HTTP_201_CREATED)
def run_connector_sync_route(payload: RunConnectorSyncRequest, session: DBSession) -> ConnectorRegistryRecordResponse:
    sync_run = run_connector_sync(session, payload)
    return _to_record_response(get_connector_registry_record(session, sync_run.connector_registry_id))


@router.get("/connectors/{connector_registry_set_id}", response_model=ConnectorRegistrySetResponse)
def get_connector_registry_set_route(
    connector_registry_set_id: str,
    session: DBSession,
) -> ConnectorRegistrySetResponse:
    return _to_set_response(get_connector_registry_set(session, connector_registry_set_id))


@router.get("/connectors", response_model=list[ConnectorRegistrySetResponse])
def list_connector_registry_sets_route(
    session: DBSession,
    scope_type: ConnectorScopeType | None = Query(default=None),
    scope_ref: str | None = Query(default=None),
) -> list[ConnectorRegistrySetResponse]:
    return [
        _to_set_response(item)
        for item in list_connector_registry_sets(session, scope_type=scope_type, scope_ref=scope_ref)
    ]


@router.get("/connectors/records/{connector_registry_id}", response_model=ConnectorRegistryRecordResponse)
def get_connector_registry_record_route(
    connector_registry_id: str,
    session: DBSession,
) -> ConnectorRegistryRecordResponse:
    return _to_record_response(get_connector_registry_record(session, connector_registry_id))
