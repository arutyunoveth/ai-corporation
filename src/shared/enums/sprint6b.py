from enum import StrEnum


class IncidentStatus(StrEnum):
    OPEN = "OPEN"
    CONTAINED = "CONTAINED"
    RESOLVED = "RESOLVED"
    STALE = "STALE"


class IncidentType(StrEnum):
    DELIVERY = "DELIVERY"
    QUALITY = "QUALITY"
    PAYMENT = "PAYMENT"
    DOCUMENT = "DOCUMENT"
    COMMUNICATION = "COMMUNICATION"
    OTHER = "OTHER"


class EscalationLevel(StrEnum):
    OWNER = "OWNER"
    SUPPLIER = "SUPPLIER"
    CUSTOMER = "CUSTOMER"
    LEGAL = "LEGAL"
    FINANCE = "FINANCE"
    OTHER = "OTHER"


class EscalationStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    DROPPED = "DROPPED"


class DealClosureStatus(StrEnum):
    READY = "READY"
    CLOSED = "CLOSED"
    FAILED = "FAILED"
    STALE = "STALE"


class DealClosureCode(StrEnum):
    CLOSED_WON = "CLOSED_WON"
    CLOSED_LOST = "CLOSED_LOST"
    CLOSED_CANCELLED = "CLOSED_CANCELLED"
    CLOSED_NO_RESULT = "CLOSED_NO_RESULT"


class KPIStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"


class LearningNoteType(StrEnum):
    WHAT_WORKED = "WHAT_WORKED"
    WHAT_FAILED = "WHAT_FAILED"
    PROCESS_GAP = "PROCESS_GAP"
    SUPPLIER_LEARNING = "SUPPLIER_LEARNING"
    CUSTOMER_LEARNING = "CUSTOMER_LEARNING"
    OTHER = "OTHER"
