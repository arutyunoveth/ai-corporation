from datetime import datetime

from pydantic import Field

from src.shared.enums import ReceiptBindingType, ReceiptSourceType, SubmissionReceiptStatus
from src.shared.types.common import APIModel


class SubmissionReceiptBindingInput(APIModel):
    artifact_ref: str
    binding_type: ReceiptBindingType


class RegisterSubmissionReceiptRequest(APIModel):
    deal_id: str
    submission_execution_set_id: str
    receipt_number: str
    receipt_timestamp: datetime
    receipt_source: ReceiptSourceType
    bindings: list[SubmissionReceiptBindingInput] = Field(default_factory=list)


class SubmissionReceiptBindingResponse(APIModel):
    artifact_ref: str
    binding_type: ReceiptBindingType
    created_at: datetime


class SubmissionReceiptRecordResponse(APIModel):
    submission_receipt_id: str
    submission_receipt_set_id: str
    receipt_number: str
    receipt_timestamp: datetime
    receipt_source: ReceiptSourceType
    created_at: datetime
    updated_at: datetime
    bindings: list[SubmissionReceiptBindingResponse]


class SubmissionReceiptSetResponse(APIModel):
    submission_receipt_set_id: str
    deal_id: str
    submission_execution_set_id: str
    receipt_status: SubmissionReceiptStatus
    created_at: datetime
    updated_at: datetime
    records: list[SubmissionReceiptRecordResponse]
