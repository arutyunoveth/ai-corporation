from enum import StrEnum


class LogisticsStatus(StrEnum):
    ACTIVE = "ACTIVE"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    ACCEPTED = "ACCEPTED"
    DELAYED = "DELAYED"
    FAILED = "FAILED"


class LogisticsEventType(StrEnum):
    CREATED = "CREATED"
    CHECKPOINT = "CHECKPOINT"
    ETA_UPDATED = "ETA_UPDATED"
    DELAY = "DELAY"
    DELIVERED = "DELIVERED"
    ACCEPTED = "ACCEPTED"
    NOTE = "NOTE"


class IncidentRegisterStatus(StrEnum):
    MONITORING = "MONITORING"
    OPEN = "OPEN"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"


class IncidentRegisterType(StrEnum):
    LOGISTICS = "LOGISTICS"
    ACCEPTANCE = "ACCEPTANCE"
    PAYMENT = "PAYMENT"
    DOCUMENT = "DOCUMENT"
    OTHER = "OTHER"


class IncidentRegisterEventType(StrEnum):
    REGISTERED = "REGISTERED"
    UPDATED = "UPDATED"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    NOTE = "NOTE"


class AcceptanceStatus(StrEnum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class AcceptanceResolutionState(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class ClosingDocsStatus(StrEnum):
    COLLECTING = "COLLECTING"
    PARTIAL = "PARTIAL"
    READY = "READY"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ClosingDocItemStatus(StrEnum):
    REQUIRED = "REQUIRED"
    PRESENT = "PRESENT"
    MISSING = "MISSING"
    OPTIONAL = "OPTIONAL"


class PaymentTrackingStatus(StrEnum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    DISPUTED = "DISPUTED"


class PaymentTrackingEventType(StrEnum):
    INVOICED = "INVOICED"
    PAYMENT_REMINDER = "PAYMENT_REMINDER"
    PARTIAL_PAYMENT = "PARTIAL_PAYMENT"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    NOTE = "NOTE"


class ClaimTriggerStatus(StrEnum):
    CLEAR = "CLEAR"
    TRIGGERED = "TRIGGERED"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
