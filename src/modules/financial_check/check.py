from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


RISK_LEVELS = ["low", "medium", "high", "critical"]


def escalate_risk_level(current: str | None, severity: str) -> str:
    base = (current or "medium").lower()
    if base not in RISK_LEVELS:
        base = "medium"

    bump = 0
    if severity == "warning":
        bump = 1
    elif severity == "error":
        bump = 2

    idx = min(RISK_LEVELS.index(base) + bump, len(RISK_LEVELS) - 1)
    return RISK_LEVELS[idx]


@dataclass
class FinancialCheckResult:
    status: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def check_purchase_financials(
    *,
    max_total_price: Decimal | None,
    margin_after_tax_percent: float | None,
    profit_after_tax: float | None,
    cash_required: float | None,
    offers: list[Any],
) -> FinancialCheckResult:
    errors: list[str] = []
    warnings: list[str] = []

    if max_total_price is not None and max_total_price <= 0:
        errors.append("max_total_price must be positive")
    if max_total_price is None:
        warnings.append("max_total_price is unknown")

    if margin_after_tax_percent is not None:
        if margin_after_tax_percent < 0:
            warnings.append(f"margin_after_tax_percent is negative: {margin_after_tax_percent:.1f}%")
        elif margin_after_tax_percent < 5:
            warnings.append(f"margin_after_tax_percent is very low: {margin_after_tax_percent:.1f}%")
    else:
        warnings.append("margin_after_tax_percent is unknown")

    if profit_after_tax is not None and profit_after_tax < 0:
        errors.append(f"profit_after_tax is negative: {profit_after_tax:.2f}")

    if cash_required is not None:
        if cash_required <= 0:
            errors.append("cash_required must be positive")
        elif max_total_price is not None and cash_required > float(max_total_price):
            warnings.append("cash_required exceeds max_total_price")
    else:
        warnings.append("cash_required is unknown")

    if not offers:
        warnings.append("no market offers found")

    status = "ok"
    if errors:
        status = "error"
    elif warnings:
        status = "warning"

    return FinancialCheckResult(status=status, errors=errors, warnings=warnings)
