from datetime import datetime

from src.shared.enums import BidPackageItemRole, BidPackageStatus
from src.shared.types.common import APIModel


class BuildBidPackageRequest(APIModel):
    deal_id: str
    bid_document_collection_set_id: str


class BidPackageItemResponse(APIModel):
    artifact_ref: str
    item_role: BidPackageItemRole
    sort_order: int
    created_at: datetime


class BidPackageRecordResponse(APIModel):
    bid_package_id: str
    bid_package_set_id: str
    package_version_no: int
    manifest_json: dict
    created_at: datetime
    updated_at: datetime
    items: list[BidPackageItemResponse]


class BidPackageSetResponse(APIModel):
    bid_package_set_id: str
    deal_id: str
    bid_document_collection_set_id: str
    package_status: BidPackageStatus
    created_at: datetime
    updated_at: datetime
    records: list[BidPackageRecordResponse]
