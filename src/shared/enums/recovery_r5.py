from enum import StrEnum


class DealClosureReportStatus(StrEnum):
    BUILT = "BUILT"
    ATTENTION_REQUIRED = "ATTENTION_REQUIRED"
    FAILED = "FAILED"


class PostmortemStatus(StrEnum):
    BUILT = "BUILT"
    ACTIONS_DEFINED = "ACTIONS_DEFINED"
    FAILED = "FAILED"


class PostmortemActionStatus(StrEnum):
    PLANNED = "PLANNED"
    TRACKED = "TRACKED"
    CLOSED = "CLOSED"


class SupplierRatingStatus(StrEnum):
    UPDATED = "UPDATED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"


class SupplierRatingBand(StrEnum):
    PREFERRED = "PREFERRED"
    APPROVED = "APPROVED"
    WATCHLIST = "WATCHLIST"
    BLOCKED = "BLOCKED"


class KnowledgeAssetStatus(StrEnum):
    BUILT = "BUILT"
    READY = "READY"
    FAILED = "FAILED"


class KnowledgeAssetType(StrEnum):
    CLOSURE_REPORT = "CLOSURE_REPORT"
    POSTMORTEM = "POSTMORTEM"
    SUPPLIER_PLAYBOOK = "SUPPLIER_PLAYBOOK"
    EXECUTION_LESSON = "EXECUTION_LESSON"
