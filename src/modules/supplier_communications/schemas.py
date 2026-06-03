from datetime import datetime

from src.shared.enums import MessageDirection, SupplierThreadStatus
from src.shared.types.common import APIModel


class BuildSupplierCommunicationSetRequest(APIModel):
    deal_id: str
    rfq_batch_id: str


class RecordSupplierMessageRequest(APIModel):
    direction: MessageDirection
    message_subject: str | None = None
    message_text: str
    linked_artifact_ref: str | None = None
    sent_at: datetime | None = None


class SupplierMessageRecordResponse(APIModel):
    supplier_message_id: str
    supplier_thread_id: str
    direction: MessageDirection
    message_subject: str | None
    message_text: str
    linked_artifact_ref: str | None
    sent_at: datetime
    created_at: datetime


class SupplierCommunicationThreadResponse(APIModel):
    supplier_thread_id: str
    supplier_communication_set_id: str
    supplier_id: str
    rfq_id: str
    thread_status: SupplierThreadStatus
    last_message_at: datetime | None
    created_at: datetime
    messages: list[SupplierMessageRecordResponse]


class SupplierCommunicationSetResponse(APIModel):
    supplier_communication_set_id: str
    deal_id: str
    rfq_batch_id: str
    created_at: datetime
    threads: list[SupplierCommunicationThreadResponse]
