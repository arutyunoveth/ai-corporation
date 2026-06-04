from datetime import datetime

from src.shared.enums import KnowledgeAssetStatus, KnowledgeAssetType
from src.shared.types.common import APIModel


class BuildKnowledgeAssetRequest(APIModel):
    deal_id: str


class KnowledgeAssetLinkResponse(APIModel):
    source_ref: str
    created_at: datetime


class KnowledgeAssetRecordResponse(APIModel):
    knowledge_asset_id: str
    asset_title: str
    asset_type: KnowledgeAssetType
    summary_text: str
    asset_payload_json: dict
    created_at: datetime
    updated_at: datetime
    links: list[KnowledgeAssetLinkResponse]


class KnowledgeAssetSetResponse(APIModel):
    knowledge_asset_set_id: str
    deal_id: str
    postmortem_set_id: str
    archive_export_set_id: str | None
    dashboard_snapshot_set_id: str | None
    knowledge_status: KnowledgeAssetStatus
    created_at: datetime
    updated_at: datetime
    records: list[KnowledgeAssetRecordResponse]
