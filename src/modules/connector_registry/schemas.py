from datetime import datetime

from src.shared.enums import (
    ConnectorRegistryStatus,
    ConnectorScopeType,
    ConnectorStatus,
    ConnectorSyncStatus,
    ConnectorType,
)
from src.shared.types.common import APIModel


class BuildConnectorRegistryRequest(APIModel):
    scope_type: ConnectorScopeType
    scope_ref: str


class RunConnectorSyncRequest(APIModel):
    connector_registry_id: str
    sync_summary: str | None = None


class ConnectorSyncRunResponse(APIModel):
    connector_sync_run_id: str
    connector_registry_id: str
    sync_status: ConnectorSyncStatus
    sync_summary: str
    started_at: datetime
    finished_at: datetime | None
    created_at: datetime


class ConnectorRegistryRecordResponse(APIModel):
    connector_registry_id: str
    connector_registry_set_id: str
    connector_code: str
    connector_type: ConnectorType
    connector_status: ConnectorStatus
    created_at: datetime
    updated_at: datetime
    sync_runs: list[ConnectorSyncRunResponse]


class ConnectorRegistrySetResponse(APIModel):
    connector_registry_set_id: str
    scope_type: ConnectorScopeType
    scope_ref: str
    registry_status: ConnectorRegistryStatus
    created_at: datetime
    updated_at: datetime
    records: list[ConnectorRegistryRecordResponse]
