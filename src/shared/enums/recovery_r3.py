from enum import StrEnum


class SupplierContractStatus(StrEnum):
    DRAFT = "DRAFT"
    READY_FOR_SIGN = "READY_FOR_SIGN"
    SIGNED = "SIGNED"
    FAILED = "FAILED"


class SupplierContractObligationStatus(StrEnum):
    PENDING = "PENDING"
    ALIGNED = "ALIGNED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ExecutionPlanStatus(StrEnum):
    BUILT = "BUILT"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"


class PurchaseOrderStatus(StrEnum):
    CREATED = "CREATED"
    SENT = "SENT"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FAILED = "FAILED"


class SupplierProgressStatus(StrEnum):
    ACTIVE = "ACTIVE"
    AT_RISK = "AT_RISK"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SupplierReadinessState(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    READY = "READY"
    DELAYED = "DELAYED"
    BLOCKED = "BLOCKED"


class SupplierProgressEventType(StrEnum):
    STATUS_UPDATE = "STATUS_UPDATE"
    READINESS_UPDATE = "READINESS_UPDATE"
    DELAY = "DELAY"
    NOTE = "NOTE"
    ALERT = "ALERT"
