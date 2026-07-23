from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from src.modules.customer_pilot.artifact_snapshot import derive_final_pdf_artifact_identity


def test_concurrent_identity_derivation_has_one_frozen_artifact_key():
    values = dict(registry_number="0379100000726000101", run_id="run-1", report_model_hash="a" * 64, customer_id="CUST-A", project_id="project", procurement_case_id="case")
    with ThreadPoolExecutor(max_workers=2) as pool:
        identities = list(pool.map(lambda _: derive_final_pdf_artifact_identity(**values), range(2)))
    assert identities[0] == identities[1]
