from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.modules.customer_pilot.artifact_snapshot import (
    derive_final_pdf_artifact_identity,
)
from src.modules.customer_pilot.artifacts import verify_review_artifact_binding


def test_derived_pdf_identity_is_stable_and_customer_scoped():
    common = dict(
        registry_number="0379100000726000101",
        run_id="run-1",
        report_model_hash="a" * 64,
        project_id="project-1",
        procurement_case_id="case-1",
    )
    first = derive_final_pdf_artifact_identity(customer_id="CUST-A", **common)
    second = derive_final_pdf_artifact_identity(customer_id="CUST-A", **common)
    foreign = derive_final_pdf_artifact_identity(customer_id="CUST-B", **common)
    assert first == second
    assert first.artifact_key == foreign.artifact_key
    assert first.pdf_relative_path != foreign.pdf_relative_path
    assert first.renderer_version == "r7-persisted-pdf-v2"


def test_review_binding_uses_verified_canonical_identity_not_artifact_aliases():
    run = SimpleNamespace(id="run", customer_id="customer", project_id="project")
    case = SimpleNamespace(id="case")
    result = SimpleNamespace(report_model_hash="r" * 64, source_graph_hash="s" * 64)
    artifact = SimpleNamespace(id="artifact", artifact_key="key", report_model_hash="x" * 64, source_graph_hash="y" * 64)
    verified = SimpleNamespace(pdf_sha256="p" * 64, renderer_version="r7-persisted-pdf-v2")
    review = SimpleNamespace(
        customer_id="customer", project_id="project", procurement_case_id="case", run_id="run",
        artifact_id="artifact", artifact_key="key", pdf_sha256="p" * 64,
        renderer_version="r7-persisted-pdf-v2", report_model_hash="r" * 64,
        source_graph_hash="s" * 64, artifact_hashes={"pdf": "p" * 64},
        immutable_at=object(), verdict="approved",
    )
    verify_review_artifact_binding(review=review, run=run, case=case, result=result, artifact=artifact, verified_artifact=verified)
    review.report_model_hash = artifact.report_model_hash
    with pytest.raises(HTTPException) as exc:
        verify_review_artifact_binding(review=review, run=run, case=case, result=result, artifact=artifact, verified_artifact=verified)
    assert exc.value.status_code == 409
