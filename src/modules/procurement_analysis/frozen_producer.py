"""Storage-neutral application boundary for the frozen R7 canonical producer.

The service owns neither HTTP nor customer/demo lifecycle.  It receives a
server-owned working directory and produces only verified frozen R7 bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.modules.procurement_analysis.canonical_persistence import (
    PersistedCanonicalFiles,
    PersistedCanonicalOutputs,
    persist_canonical_outputs,
    verify_persisted_canonical_outputs,
)


@dataclass(frozen=True)
class FrozenCanonicalProduction:
    registry_number: str
    source_analysis_run_id: str
    persisted: PersistedCanonicalOutputs
    requirements: dict[str, Any]
    canonical_model: dict[str, Any]
    source_graph: dict[str, Any]
    source_graph_hash: str
    production_model_hash: str
    report_model_hash: str


def persist_frozen_r7_outputs(
    *,
    output_dir: Path,
    run_id: str,
    metadata: dict[str, Any],
    outputs: dict[str, Any],
    steps: list[Any],
    render_html: Any,
    now_factory: Any,
) -> PersistedCanonicalFiles:
    """Shared R7 persistence seam used by the demo compatibility wrapper.

    It intentionally does not apply the R8 strict verifier: old R7 lifecycle
    remains frozen, while customer publication verifies bytes separately.
    """
    return persist_canonical_outputs(
        output_dir=output_dir,
        run_id=run_id,
        metadata=metadata,
        outputs=outputs,
        steps=steps,
        render_html=render_html,
        now_factory=now_factory,
    )


def produce_frozen_canonical_analysis(
    *,
    registry_number: str,
    run_id: str,
    output_dir: Path,
    metadata: dict[str, Any],
    documents: list[Any],
    source_analysis_run_id: str | None = None,
) -> FrozenCanonicalProduction:
    """Run R7's canonical output construction and verify exact persisted bytes.

    The R7 builder remains the sole producer of `ProcurementSourceGraph` and
    `CanonicalProcurementModel`; this adapter intentionally adds no customer
    report schema, chunks, markdown, or source graph implementation.
    """
    # These imports are intentionally local: the demo module remains the
    # compatibility facade while the application contract stays storage-neutral.
    from src.modules.tender_operator_agent_demo.upload_service import (
        _build_final_recommendation,
        _build_output_payloads,
        _build_steps_from_outputs,
        _render_canonical_report_html,
        _safe_datetime,
    )

    owned = dict(metadata)
    owned.update(
        {
            "run_id": run_id,
            "procurement_id": owned.get("procurement_id") or registry_number,
            "tender_title": owned.get("tender_title") or f"Закупка {registry_number}",
            "tender_category": owned.get("tender_category") or "Закупка",
            "customer_name": owned.get("customer_name") or "Не указан",
            "status": "completed",
            "warnings": list(owned.get("warnings") or []),
            "limitations": list(owned.get("limitations") or []),
            "files": list(owned.get("files") or []),
            "mode": "frozen_customer_pilot",
        }
    )
    outputs = _build_output_payloads(
        metadata=owned,
        documents=documents,
        analysis_mode="frozen_r7_production",
        requirements={
            "technical_requirements": [],
            "document_requirements": [],
            "qualification_requirements": [],
            "evaluation_criteria": [],
        },
        calibrated_risks=[],
        supplier_questions=[],
        tkp_comparison=None,
        economics=None,
        bid_decision=None,
        core_complete=False,
        quote_inputs_present=False,
    )
    steps = _build_steps_from_outputs(owned, outputs)
    # Builds the frozen recommendation as part of the same R7 output pipeline.
    _build_final_recommendation(outputs)
    persisted_files = persist_canonical_outputs(
        output_dir=output_dir,
        run_id=run_id,
        metadata=owned,
        outputs=outputs,
        steps=steps,
        render_html=_render_canonical_report_html,
        now_factory=_safe_datetime,
    )
    verified = verify_persisted_canonical_outputs(
        output_dir=output_dir,
        expected_outputs=outputs,
        expected_canonical_report=persisted_files.canonical_report,
    )
    requirements = __import__("json").loads(verified.requirements_bytes)
    canonical_model = requirements["preliminary_analysis"][
        "canonical_procurement_model"
    ]
    return FrozenCanonicalProduction(
        registry_number=registry_number,
        source_analysis_run_id=source_analysis_run_id or str(uuid4()),
        persisted=verified,
        requirements=requirements,
        canonical_model=canonical_model,
        source_graph=verified.source_graph,
        source_graph_hash=verified.source_graph_hash,
        production_model_hash=verified.production_model_hash,
        report_model_hash=verified.report_model_hash,
    )
