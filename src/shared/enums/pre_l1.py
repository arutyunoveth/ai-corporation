from enum import StrEnum


class LaunchVisibilityScopeType(StrEnum):
    DEAL = "DEAL"
    PILOT = "PILOT"


class LaunchVisibilityStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"


class LaunchVisibilityItemType(StrEnum):
    OVERVIEW = "OVERVIEW"
    ATTENTION = "ATTENTION"
    RED_FLAG = "RED_FLAG"
    HOTSPOT = "HOTSPOT"
