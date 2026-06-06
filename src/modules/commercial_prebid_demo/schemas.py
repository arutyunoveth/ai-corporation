from datetime import datetime

from pydantic import Field

from src.shared.types.common import APIModel


class RunCommercialPreBidDemoRequest(APIModel):
    fixture_name: str = Field(default="commercial_mvp_demo", min_length=1)


class CommercialPreBidDemoResponse(APIModel):
    fixture_name: str
    analysis_mode: str
    generated_at: datetime
    deal_id: str
    intake_id: str
    document_set_id: str
    tender_summary_id: str
    requirement_extraction_set_id: str
    document_requirement_set_id: str
    risk_flag_set_id: str
    contract_risk_set_id: str
    report_markdown: str
    report_json: dict
