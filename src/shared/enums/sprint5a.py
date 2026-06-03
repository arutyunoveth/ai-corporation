from enum import StrEnum


class BidDocumentCollectionStatus(StrEnum):
    BUILT = "BUILT"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    STALE = "STALE"


class BidDocumentRowStatus(StrEnum):
    COLLECTED = "COLLECTED"
    MISSING = "MISSING"
    WAIVED = "WAIVED"
    PENDING = "PENDING"


class BidPackageStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"


class BidPackageItemRole(StrEnum):
    PRIMARY_DOC = "PRIMARY_DOC"
    ATTACHMENT = "ATTACHMENT"
    FORM = "FORM"
    DECLARATION = "DECLARATION"
    OTHER = "OTHER"


class BidCompletenessStatus(StrEnum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class SubmissionReadinessStatus(StrEnum):
    READY = "READY"
    NOT_READY = "NOT_READY"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ReadinessRecommendation(StrEnum):
    READY = "READY"
    NOT_READY = "NOT_READY"
    NEEDS_REVIEW = "NEEDS_REVIEW"
