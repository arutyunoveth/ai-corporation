from fastapi import APIRouter, Query, status

from src.modules.bid_documents.schemas import (
    BidDocumentCollectionBindingResponse,
    BidDocumentCollectionRowResponse,
    BidDocumentCollectionSetResponse,
    BuildBidDocumentCollectionRequest,
)
from src.modules.bid_documents.service import (
    build_bid_document_collection,
    get_bid_document_collection_set,
    list_bid_document_collection_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["bid-documents"])


def _to_set_response(result: tuple) -> BidDocumentCollectionSetResponse:
    collection_set, rows, bindings = result
    return BidDocumentCollectionSetResponse(
        bid_document_collection_set_id=collection_set.bid_document_collection_set_id,
        deal_id=collection_set.deal_id,
        document_requirement_set_id=collection_set.document_requirement_set_id,
        ceo_approval_set_id=collection_set.ceo_approval_set_id,
        collection_status=collection_set.collection_status,
        created_at=collection_set.created_at,
        updated_at=collection_set.updated_at,
        rows=[BidDocumentCollectionRowResponse.model_validate(item) for item in rows],
        bindings=[BidDocumentCollectionBindingResponse.model_validate(item) for item in bindings],
    )


@router.post("/bid-documents/collect", response_model=BidDocumentCollectionSetResponse, status_code=status.HTTP_201_CREATED)
def build_bid_document_collection_route(
    payload: BuildBidDocumentCollectionRequest,
    session: DBSession,
) -> BidDocumentCollectionSetResponse:
    collection_set = build_bid_document_collection(session, payload)
    return _to_set_response(get_bid_document_collection_set(session, collection_set.bid_document_collection_set_id))


@router.get("/bid-documents/{bid_document_collection_set_id}", response_model=BidDocumentCollectionSetResponse)
def get_bid_document_collection_set_route(
    bid_document_collection_set_id: str,
    session: DBSession,
) -> BidDocumentCollectionSetResponse:
    return _to_set_response(get_bid_document_collection_set(session, bid_document_collection_set_id))


@router.get("/bid-documents", response_model=list[BidDocumentCollectionSetResponse])
def list_bid_document_collection_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[BidDocumentCollectionSetResponse]:
    return [_to_set_response(item) for item in list_bid_document_collection_sets(session, deal_id=deal_id)]


@router.get("/bid-documents/rows/{bid_document_collection_set_id}", response_model=list[BidDocumentCollectionRowResponse])
def get_bid_document_collection_rows_route(
    bid_document_collection_set_id: str,
    session: DBSession,
) -> list[BidDocumentCollectionRowResponse]:
    _collection_set, rows, _bindings = get_bid_document_collection_set(session, bid_document_collection_set_id)
    return [BidDocumentCollectionRowResponse.model_validate(item) for item in rows]
