from fastapi import APIRouter, Query, status

from src.modules.archive_export.schemas import (
    ArchiveExportItemResponse,
    ArchiveExportRecordResponse,
    ArchiveExportSetResponse,
    BuildArchiveExportRequest,
)
from src.modules.archive_export.service import (
    build_archive_export,
    get_archive_export_record,
    get_archive_export_set,
    list_archive_export_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["archive-export"])


def _to_item_response(item) -> ArchiveExportItemResponse:
    return ArchiveExportItemResponse.model_validate(item)


def _to_record_response(result: tuple) -> ArchiveExportRecordResponse:
    record, items = result
    return ArchiveExportRecordResponse(
        archive_export_id=record.archive_export_id,
        archive_export_set_id=record.archive_export_set_id,
        export_manifest_json=record.export_manifest_json,
        export_format=record.export_format,
        created_at=record.created_at,
        updated_at=record.updated_at,
        items=[_to_item_response(item) for item in items],
    )


def _to_set_response(result: tuple) -> ArchiveExportSetResponse:
    export_set, records = result
    return ArchiveExportSetResponse(
        archive_export_set_id=export_set.archive_export_set_id,
        deal_id=export_set.deal_id,
        deal_closure_set_id=export_set.deal_closure_set_id,
        export_status=export_set.export_status,
        created_at=export_set.created_at,
        updated_at=export_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/archive-export/build", response_model=ArchiveExportSetResponse, status_code=status.HTTP_201_CREATED)
def build_archive_export_route(payload: BuildArchiveExportRequest, session: DBSession) -> ArchiveExportSetResponse:
    export_set = build_archive_export(session, payload)
    return _to_set_response(get_archive_export_set(session, export_set.archive_export_set_id))


@router.get("/archive-export/{archive_export_set_id}", response_model=ArchiveExportSetResponse)
def get_archive_export_set_route(archive_export_set_id: str, session: DBSession) -> ArchiveExportSetResponse:
    return _to_set_response(get_archive_export_set(session, archive_export_set_id))


@router.get("/archive-export", response_model=list[ArchiveExportSetResponse])
def list_archive_export_sets_route(
    session: DBSession, deal_id: str | None = Query(default=None)
) -> list[ArchiveExportSetResponse]:
    return [_to_set_response(item) for item in list_archive_export_sets(session, deal_id=deal_id)]


@router.get("/archive-export/records/{archive_export_id}", response_model=ArchiveExportRecordResponse)
def get_archive_export_record_route(archive_export_id: str, session: DBSession) -> ArchiveExportRecordResponse:
    return _to_record_response(get_archive_export_record(session, archive_export_id))
