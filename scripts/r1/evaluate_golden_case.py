#!/usr/bin/env python3
"""Deterministic R1 hard-gate evaluator; deliberately contains no LLM calls."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

REGISTRY_RE = re.compile(r"(?<!\d)(?:0\d{18}|\d{19})(?!\d)")
SECTION = "Что нужно поставить"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


def _foreign_numbers(value: Any, expected: str) -> list[str]:
    return sorted({number for text in _strings(value) for number in REGISTRY_RE.findall(text) if number != expected})


def evaluate(*, registry_number: str, run_id: str, source_inventory: dict, extraction: dict,
             analysis: dict, canonical_report: dict, html: str, docx_text: str = "", pdf_text: str = "") -> tuple[dict, dict]:
    defects: list[dict[str, Any]] = []
    def fail(identifier: str, layer: str, observed: Any, expected: Any, hint: str, severity: str = "critical") -> None:
        defects.append({"id": identifier, "layer": layer, "severity": severity, "observed": observed,
                        "expected": expected, "diagnostic_hint": [hint], "related_files": []})

    all_structured = [source_inventory, extraction, analysis, canonical_report]
    foreign = sorted({item for artifact in all_structured for item in _foreign_numbers(artifact, registry_number)})
    foreign += [item for item in _foreign_numbers(html, registry_number) if item not in foreign]
    if foreign:
        fail("TENANT-001", "isolation", {"foreign_registry_numbers": foreign}, [], "Remove foreign procurement data before rendering.")

    documents = source_inventory.get("documents", extraction.get("documents", []))
    if not documents:
        fail("DOC-001", "source_inventory", {"documents": 0}, ">=1", "Acquire owned real source documents.")
    for document in documents:
        if document.get("tender_id") and str(document.get("tender_id")) != str(extraction.get("tender_id", document.get("tender_id"))):
            fail("TENANT-002", "ownership", document, "current tender", "Reject document from another tender.")
        if not document.get("processing_status") and not document.get("text_extraction_status"):
            fail("DOC-002", "source_inventory", document, "processing status", "Record extraction status for every document.")

    for artifact in all_structured:
        artifact_run = artifact.get("run_id")
        if artifact_run and artifact_run != run_id:
            fail("TENANT-004", "run_isolation", {"run_id": artifact_run}, run_id, "Do not reuse prior run artifact.")

    items = extraction.get("line_items") or analysis.get("line_items") or []
    goods = extraction.get("procurement_kind") == "goods" or analysis.get("procurement_kind") == "goods"
    if goods and not items:
        fail("EXTR-001", "extraction", {"line_items": 0}, ">=1", "Goods procurement needs extracted positions.")
    if not items:
        fail("EXTR-002", "extraction", {"line_items": 0}, ">=1", "Extract positions or mark the run blocked.")
    document_ids = {str(d.get("document_id") or d.get("id")) for d in documents}
    for index, item in enumerate(items):
        prefix = f"line_items[{index}]"
        if not (item.get("raw_name") or item.get("name") or item.get("normalized_name")):
            fail("EXTR-003", "extraction", {"item": index}, "name", f"{prefix} needs a name.")
        if not item.get("quantity") and not item.get("missing_reason"):
            fail("EXTR-004", "extraction", {"item": index}, "quantity or missing_reason", f"{prefix} silently lacks quantity.")
        if not item.get("unit") and not item.get("missing_reason"):
            fail("EXTR-005", "extraction", {"item": index}, "unit or missing_reason", f"{prefix} silently lacks unit.")
        did = str(item.get("source_document_id") or "")
        if not did:
            fail("EVD-001", "evidence", {"item": index}, "source_document_id", f"{prefix} has no evidence document.")
        elif did not in document_ids:
            fail("EVD-003", "evidence", {"source_document_id": did}, "owned document", f"{prefix} references foreign evidence.")
        if not item.get("source_quote"):
            fail("EVD-002", "evidence", {"item": index}, "source_quote", f"{prefix} has no quote.")

    report_items = canonical_report.get("positions") or canonical_report.get("line_items") or []
    if not report_items:
        fail("RPT-001", "report", {}, "positions", "Canonical model lacks positions.")
    if SECTION not in html:
        fail("RPT-002", "report", {}, SECTION, "HTML does not render positions section.")
    if docx_text and SECTION not in docx_text:
        fail("RPT-003", "report", {}, SECTION, "DOCX does not render positions section.")
    if pdf_text and SECTION not in pdf_text:
        fail("RPT-004", "report", {}, SECTION, "PDF does not render positions section.", "high")
    if len(report_items) != len(items):
        fail("RPT-005", "report", {"report": len(report_items), "analysis": len(items)}, "equal counts", "Render from the current canonical model.")

    critical = sum(item["severity"] == "critical" for item in defects)
    result = {"case_id": registry_number, "run_id": run_id, "status": "passed" if not critical else "failed",
              "score": 100 if not critical else 0, "critical_failures": critical,
              "high_failures": sum(item["severity"] == "high" for item in defects),
              "foreign_registry_numbers": foreign,
              "final_status": "AUTO_GATES_PASS_HUMAN_REVIEW_REQUIRED" if not critical else "failed"}
    return result, {**result, "defects": defects}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry-number", required=True); parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-inventory", type=Path, required=True); parser.add_argument("--extraction", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True); parser.add_argument("--canonical-report", type=Path, required=True)
    parser.add_argument("--html", type=Path, required=True); parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result, defects = evaluate(registry_number=args.registry_number, run_id=args.run_id, source_inventory=_read_json(args.source_inventory), extraction=_read_json(args.extraction), analysis=_read_json(args.analysis), canonical_report=_read_json(args.canonical_report), html=args.html.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "quality_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "defects.json").write_text(json.dumps(defects, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if result["status"] == "passed" else 1

if __name__ == "__main__":
    raise SystemExit(main())
