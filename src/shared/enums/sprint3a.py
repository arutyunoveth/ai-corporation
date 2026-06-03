from enum import StrEnum


class SupplierStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BLACKLISTED = "BLACKLISTED"
    DRAFT = "DRAFT"


class SupplierShortlistStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"


class RFQBatchStatus(StrEnum):
    BUILT = "BUILT"
    READY_TO_SEND = "READY_TO_SEND"
    SENT = "SENT"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class RFQStatus(StrEnum):
    BUILT = "BUILT"
    SENT = "SENT"
    REPLIED = "REPLIED"
    CLOSED = "CLOSED"


class SupplierThreadStatus(StrEnum):
    OPEN = "OPEN"
    WAITING_REPLY = "WAITING_REPLY"
    REPLIED = "REPLIED"
    CLOSED = "CLOSED"


class MessageDirection(StrEnum):
    OUTBOUND = "OUTBOUND"
    INBOUND = "INBOUND"


class QuoteStatus(StrEnum):
    RECEIVED = "RECEIVED"
    REVISED = "REVISED"
    WITHDRAWN = "WITHDRAWN"
