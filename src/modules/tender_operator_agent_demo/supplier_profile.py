from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from src.shared.types.common import APIModel


class RiskTolerance(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SupplierProfileCriteria(APIModel):
    categories: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    price_min: float | None = None
    price_max: float | None = None
    keywords: list[str] = Field(default_factory=list)
    stop_words: list[str] = Field(default_factory=list)


class SupplierProfileRiskPreferences(APIModel):
    tolerance: RiskTolerance = RiskTolerance.MEDIUM
    max_penalty_percent: float | None = None
    max_delay_days: int | None = None
    require_certificates: bool = True


class SupplierProfile(APIModel):
    supplier_id: str
    name: str
    short_name: str | None = None
    inn: str | None = None
    description: str | None = None
    criteria: SupplierProfileCriteria = Field(default_factory=SupplierProfileCriteria)
    risk_preferences: SupplierProfileRiskPreferences = Field(default_factory=SupplierProfileRiskPreferences)
    certificates: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def load_demo_fixture(cls) -> SupplierProfile:
        import json
        import os

        fixture_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "demo_data", "tender_operator_agent",
            "supplier_profile_electrical.json",
        )
        resolved = os.path.normpath(fixture_path)
        if not os.path.isfile(resolved):
            raise FileNotFoundError(
                f"Demo supplier profile fixture not found at {resolved}. "
                "Ensure demo_data/tender_operator_agent/supplier_profile_electrical.json exists."
            )
        with open(resolved, encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
