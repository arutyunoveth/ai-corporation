from fastapi import APIRouter, Query, status

from src.modules.bid_packages.schemas import (
    BidPackageItemResponse,
    BidPackageRecordResponse,
    BidPackageSetResponse,
    BuildBidPackageRequest,
)
from src.modules.bid_packages.service import (
    build_bid_package,
    get_bid_package_record,
    get_bid_package_set,
    list_bid_package_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["bid-packages"])


def _to_record_response(result: tuple) -> BidPackageRecordResponse:
    record, items = result
    return BidPackageRecordResponse(
        bid_package_id=record.bid_package_id,
        bid_package_set_id=record.bid_package_set_id,
        package_version_no=record.package_version_no,
        manifest_json=record.manifest_json,
        created_at=record.created_at,
        updated_at=record.updated_at,
        items=[BidPackageItemResponse.model_validate(item) for item in items],
    )


def _to_set_response(result: tuple) -> BidPackageSetResponse:
    package_set, records = result
    return BidPackageSetResponse(
        bid_package_set_id=package_set.bid_package_set_id,
        deal_id=package_set.deal_id,
        bid_document_collection_set_id=package_set.bid_document_collection_set_id,
        package_status=package_set.package_status,
        created_at=package_set.created_at,
        updated_at=package_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/bid-packages/build", response_model=BidPackageSetResponse, status_code=status.HTTP_201_CREATED)
def build_bid_package_route(
    payload: BuildBidPackageRequest,
    session: DBSession,
) -> BidPackageSetResponse:
    package_set = build_bid_package(session, payload)
    return _to_set_response(get_bid_package_set(session, package_set.bid_package_set_id))


@router.get("/bid-packages/{bid_package_set_id}", response_model=BidPackageSetResponse)
def get_bid_package_set_route(bid_package_set_id: str, session: DBSession) -> BidPackageSetResponse:
    return _to_set_response(get_bid_package_set(session, bid_package_set_id))


@router.get("/bid-packages", response_model=list[BidPackageSetResponse])
def list_bid_package_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[BidPackageSetResponse]:
    return [_to_set_response(item) for item in list_bid_package_sets(session, deal_id=deal_id)]


@router.get("/bid-packages/records/{bid_package_id}", response_model=BidPackageRecordResponse)
def get_bid_package_record_route(bid_package_id: str, session: DBSession) -> BidPackageRecordResponse:
    return _to_record_response(get_bid_package_record(session, bid_package_id))
