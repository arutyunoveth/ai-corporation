from enum import StrEnum


class SupplierVerificationStatus(StrEnum):
    BUILT = "BUILT"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class SupplierVerificationResult(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class VerificationFlagSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class QuoteComparisonStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"
