#!/usr/bin/env python3
"""Deterministic gates for a source-backed procurement analysis candidate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any



def _load(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle) if path.suffix == ".json" else handle.read()


def _all_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_all_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_all_text(item) for item in value)
    return str(value or "")


def evaluate(case: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    expected = _load(case / "expected_analysis.yaml")
    evidence_text = _load(case / "expected_evidence.yaml")
    expected_count = 43 if case.name == "0352300080626000109" else None
    context = candidate.get("analysis_context", candidate.get("requirements", {}).get("analysis_context", candidate))
    preliminary = candidate.get("preliminary_analysis", candidate.get("requirements", {}).get("preliminary_analysis", {}))
    coverage = preliminary.get("item_coverage", context.get("item_coverage", {}))
    text = _all_text(candidate).lower()
    prohibited = ("обучени", "смэв", "интеграц", "внедрени", " api", "программное обеспеч", "преподавател", "аудитори")
    gates: dict[str, bool] = {
        "category_services": context.get("procurement_category", preliminary.get("procurement_kind")) == "services",
        "subject_consistent": "диагностик" in text and "ремонт" in text,
        "okpd2_consistent": str(context.get("okpd2", "")).startswith("45.20"),
        "item_count_received": expected_count is None or coverage.get("extracted_item_count") == expected_count,
        "item_count_analyzed": expected_count is None or coverage.get("analyzed_item_count") == expected_count,
        "no_ignored_items": coverage.get("ignored_item_count") == 0,
        "evidence_coverage": coverage.get("item_evidence_coverage") == 1.0,
        "missing_contract_disclosed": "draft_contract" in context.get("missing_documents", preliminary.get("missing_documents", [])),
        "prohibited_claims": not any(token in text for token in prohibited),
        "decision_not_unconditional_go": candidate.get("final_recommendation", {}).get("recommendation") != "participate_conditionally",
        "source_not_complete": context.get("document_coverage") != "complete",
        "evidence_fixture_present": "evidence_id:" in evidence_text,
        "expected_status": "status: needs_review" in expected,
    }
    failed = [name for name, passed in gates.items() if not passed]
    return {"status": "passed" if not failed else "failed", "case_id": case.name, "gates": gates, "failed_gates": failed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.case, _load(args.candidate))
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
