from enum import StrEnum


class SubmissionArchiveStatus(StrEnum):
    BUILT = "BUILT"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class SubmissionArchiveItemRole(StrEnum):
    BID_PACKAGE_ITEM = "BID_PACKAGE_ITEM"
    SUBMISSION_PROOF = "SUBMISSION_PROOF"
    RECEIPT_EVIDENCE = "RECEIPT_EVIDENCE"
    OTHER = "OTHER"


class ProcedureStatus(StrEnum):
    BID_IN_PROGRESS = "BID_IN_PROGRESS"
    WON_PENDING_CONTRACT = "WON_PENDING_CONTRACT"
    LOST = "LOST"
    CANCELLED = "CANCELLED"


class ProcedureMonitorEventType(StrEnum):
    STATUS_UPDATE = "STATUS_UPDATE"
    NOTICE = "NOTICE"
    OUTCOME = "OUTCOME"
    ALERT = "ALERT"
    OTHER = "OTHER"


class ContractNegotiationStatus(StrEnum):
    OPEN = "OPEN"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    READY_TO_NEGOTIATE = "READY_TO_NEGOTIATE"
    FAILED = "FAILED"
