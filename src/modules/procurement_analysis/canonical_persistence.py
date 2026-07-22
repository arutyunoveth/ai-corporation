"""Frozen R7 canonical-output persistence, independent of a run-root adapter."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class PersistedCanonicalOutputs:
    requirements_path: Path
    canonical_report_path: Path
    report_json_path: Path
    report_html_path: Path
    steps_path: Path
    canonical_report: dict[str, Any]
    source_graph: dict[str, Any]
    production_model_hash: str
    report_model_hash: str
    requirements_file_sha256: str
    canonical_report_file_sha256: str


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    # Frozen R7 contract: indent=2 and intentionally no trailing newline.
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def persist_canonical_outputs(*, output_dir: Path, run_id: str, metadata: dict, outputs: dict, steps: list, render_html: Callable[[dict], str], now_factory: Callable[[], str]) -> PersistedCanonicalOutputs:
    from src.modules.tender_operator_agent_demo.report_model import build_procurement_report_model, canonical_report_to_markdown
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in outputs.items():
        _write_json(output_dir / f"{name}.json", payload)
    canonical = build_procurement_report_model(metadata, outputs)
    canonical_path = output_dir / "canonical_report.json"; _write_json(canonical_path, canonical)
    html_path = output_dir / "report.html"; html_path.write_text(render_html(canonical), encoding="utf-8")
    report_path = output_dir / "report.json"
    _write_json(report_path, {"run_id": run_id, "report_title": "Отчёт по загруженному прогону тендерного агента", "generated_at": now_factory(), "recommendation": outputs["final_recommendation"]["recommendation"], "recommendation_label": outputs["final_recommendation"]["label"], "executive_summary": outputs["final_recommendation"]["rationale"], "manual_checks": outputs["final_recommendation"]["manual_checks"], "sections": [{"title": item.title, "kind": "bullets", "items": item.findings} for item in steps], "report_markdown": canonical_report_to_markdown(canonical)})
    steps_path = output_dir / "steps.json"; _write_json(steps_path, {"steps": [item.model_dump(mode="json") for item in steps]})
    requirements_path = output_dir / "requirements.json"
    try:
        preliminary = outputs["requirements"]["preliminary_analysis"]
        canonical_model = preliminary["canonical_procurement_model"]
        graph = canonical_model["source_graph"]
        production_hash = canonical_model["production_model_hash"]
    except (KeyError, TypeError) as exc:
        raise ValueError("Frozen R7 canonical source-graph contract is incomplete") from exc
    if not isinstance(graph, dict) or not production_hash:
        raise ValueError("Frozen R7 canonical source-graph contract is invalid")
    if canonical.get("provenance", {}).get("production_model_hash") != production_hash:
        raise ValueError("Frozen R7 production model hash mismatch")
    model_hash = hashlib.sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return PersistedCanonicalOutputs(requirements_path, canonical_path, report_path, html_path, steps_path, canonical, graph, production_hash, model_hash, hashlib.sha256(requirements_path.read_bytes()).hexdigest(), hashlib.sha256(canonical_path.read_bytes()).hexdigest())
