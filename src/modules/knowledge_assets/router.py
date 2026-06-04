from fastapi import APIRouter, Query, status

from src.modules.knowledge_assets.schemas import (
    BuildKnowledgeAssetRequest,
    KnowledgeAssetLinkResponse,
    KnowledgeAssetRecordResponse,
    KnowledgeAssetSetResponse,
)
from src.modules.knowledge_assets.service import (
    build_knowledge_asset,
    get_knowledge_asset_record,
    get_knowledge_asset_set,
    list_knowledge_asset_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["knowledge-assets"])


def _to_record_response(result: tuple) -> KnowledgeAssetRecordResponse:
    record, links = result
    return KnowledgeAssetRecordResponse(
        knowledge_asset_id=record.knowledge_asset_id,
        asset_title=record.asset_title,
        asset_type=record.asset_type,
        summary_text=record.summary_text,
        asset_payload_json=record.asset_payload_json,
        created_at=record.created_at,
        updated_at=record.updated_at,
        links=[KnowledgeAssetLinkResponse.model_validate(item) for item in links],
    )


def _to_set_response(result: tuple) -> KnowledgeAssetSetResponse:
    asset_set, records = result
    return KnowledgeAssetSetResponse(
        knowledge_asset_set_id=asset_set.knowledge_asset_set_id,
        deal_id=asset_set.deal_id,
        postmortem_set_id=asset_set.postmortem_set_id,
        archive_export_set_id=asset_set.archive_export_set_id,
        dashboard_snapshot_set_id=asset_set.dashboard_snapshot_set_id,
        knowledge_status=asset_set.knowledge_status,
        created_at=asset_set.created_at,
        updated_at=asset_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/knowledge-assets/build", response_model=KnowledgeAssetSetResponse, status_code=status.HTTP_201_CREATED)
def build_knowledge_asset_route(
    payload: BuildKnowledgeAssetRequest,
    session: DBSession,
) -> KnowledgeAssetSetResponse:
    asset_set = build_knowledge_asset(session, payload)
    return _to_set_response(get_knowledge_asset_set(session, asset_set.knowledge_asset_set_id))


@router.get("/knowledge-assets/{knowledge_asset_set_id}", response_model=KnowledgeAssetSetResponse)
def get_knowledge_asset_set_route(
    knowledge_asset_set_id: str,
    session: DBSession,
) -> KnowledgeAssetSetResponse:
    return _to_set_response(get_knowledge_asset_set(session, knowledge_asset_set_id))


@router.get("/knowledge-assets", response_model=list[KnowledgeAssetSetResponse])
def list_knowledge_asset_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[KnowledgeAssetSetResponse]:
    return [_to_set_response(item) for item in list_knowledge_asset_sets(session, deal_id=deal_id)]


@router.get("/knowledge-assets/records/{knowledge_asset_id}", response_model=KnowledgeAssetRecordResponse)
def get_knowledge_asset_record_route(
    knowledge_asset_id: str,
    session: DBSession,
) -> KnowledgeAssetRecordResponse:
    return _to_record_response(get_knowledge_asset_record(session, knowledge_asset_id))
