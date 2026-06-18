from enum import StrEnum


class AgentRegistryStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"


class AgentLifecycleStatus(StrEnum):
    REVIEWED = "REVIEWED"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


class AgentActivationState(StrEnum):
    REVIEWED = "REVIEWED"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


class HumanReviewStatus(StrEnum):
    DRAFT = "draft"
    NEEDS_VALIDATION = "needs_validation"
    VALIDATION_FAILED = "validation_failed"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    APPROVED_FOR_INTERNAL_USE = "approved_for_internal_use"
    APPROVED_FOR_EXTERNAL_USE = "approved_for_external_use"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class PromptSchemaLibraryStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"


class PromptSchemaAssetStatus(StrEnum):
    REVIEWED = "REVIEWED"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


class PromptValidationMode(StrEnum):
    NONE = "NONE"
    SCHEMA_REQUIRED = "SCHEMA_REQUIRED"
    STRICT = "STRICT"


class PromptRiskClass(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RuntimeTraceActorType(StrEnum):
    AGENT_PROFILE = "AGENT_PROFILE"
    OPERATOR = "OPERATOR"
    SYSTEM = "SYSTEM"


class RuntimeTraceActionType(StrEnum):
    GENERATE_DRAFT = "GENERATE_DRAFT"
    VALIDATE_OUTPUT = "VALIDATE_OUTPUT"
    REVIEW_OUTPUT = "REVIEW_OUTPUT"
    LINK_METADATA = "LINK_METADATA"


class RuntimeTraceValidationStatus(StrEnum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"


class RuntimeTraceDisposition(StrEnum):
    DRAFT = "DRAFT"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"
    APPROVED_FOR_INTERNAL_USE = "APPROVED_FOR_INTERNAL_USE"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class RuntimeMetadataSliceStatus(StrEnum):
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    APPROVED_FOR_INTERNAL_USE = "approved_for_internal_use"
    REJECTED = "rejected"


class PromptSchemaAssetType(StrEnum):
    PROMPT_TEMPLATE = "PROMPT_TEMPLATE"
    INPUT_SCHEMA = "INPUT_SCHEMA"
    OUTPUT_SCHEMA = "OUTPUT_SCHEMA"
    COMPOSITE = "COMPOSITE"


class AgentPromptLinkStatus(StrEnum):
    APPROVED = "APPROVED"
    DISABLED = "DISABLED"


class AgentScope(StrEnum):
    PRODUCT = "product"
    COMPANY_OPERATIONS = "company_operations"
    PLATFORM = "platform"


class AgentKind(StrEnum):
    OPERATING_SYSTEM = "operating_system"
    TENDER_OPERATIONS = "tender_operations"
    RISK_FINANCE_LEGAL = "risk_finance_legal"
    ENGINEERING = "engineering"
    GROWTH = "growth"
    DELIVERY = "delivery"
    RESEARCH = "research"


class CompanyAgentActivationState(StrEnum):
    DRAFT = "draft"
    ACTIVE_METADATA_ONLY = "active_metadata_only"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"


class DataPolicy(StrEnum):
    LOCAL_ONLY = "local_only"
    LOCAL_FIRST = "local_first"
    HYBRID_PUBLIC_ONLY = "hybrid_public_only"


class RuntimeMode(StrEnum):
    METADATA_ONLY = "metadata_only"
    MANUAL_CONTEXT_ONLY = "manual_context_only"
    DEFERRED_EXECUTION = "deferred_execution"


class ModelTier(StrEnum):
    REASONING = "reasoning"
    STANDARD = "standard"
    CODE_REASONING = "code_reasoning"
    WRITING = "writing"
