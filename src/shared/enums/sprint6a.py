from enum import StrEnum


class DeliveryLaunchStatus(StrEnum):
    READY = "READY"
    BLOCKED = "BLOCKED"
    LAUNCHED = "LAUNCHED"
    FAILED = "FAILED"


class LaunchRecommendation(StrEnum):
    READY = "READY"
    BLOCKED = "BLOCKED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ExecutionCommandStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ON_HOLD = "ON_HOLD"
    FAILED = "FAILED"


class ExecutionPhase(StrEnum):
    LAUNCHED = "LAUNCHED"
    PROCUREMENT = "PROCUREMENT"
    SHIPPING = "SHIPPING"
    ACCEPTANCE = "ACCEPTANCE"
    INVOICING = "INVOICING"
    COLLECTION = "COLLECTION"
    CLOSED = "CLOSED"


class DeliveryMilestoneStatus(StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    STALE = "STALE"


class MilestoneState(StrEnum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    DELAYED = "DELAYED"
    CANCELLED = "CANCELLED"


class SupplierFulfillmentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    AT_RISK = "AT_RISK"
    FAILED = "FAILED"


class SupplierFulfillmentState(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    FULFILLED = "FULFILLED"
    DELAYED = "DELAYED"
    FAILED = "FAILED"


class ShippingAcceptanceStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DELIVERED = "DELIVERED"
    ACCEPTED = "ACCEPTED"
    FAILED = "FAILED"
    STALE = "STALE"


class ShippingAcceptanceState(StrEnum):
    PLANNED = "PLANNED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class PaymentCollectionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INVOICED = "INVOICED"
    PARTIALLY_COLLECTED = "PARTIALLY_COLLECTED"
    COLLECTED = "COLLECTED"
    FAILED = "FAILED"


class CollectionState(StrEnum):
    NOT_INVOICED = "NOT_INVOICED"
    INVOICED = "INVOICED"
    PARTIAL = "PARTIAL"
    COLLECTED = "COLLECTED"
    OVERDUE = "OVERDUE"
