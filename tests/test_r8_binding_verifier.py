from src.modules.customer_pilot.binding_verifier import VerifiedRunSnapshotBinding


def test_verified_binding_contract_exposes_all_independent_hashes():
    assert {
        "requirements_file_sha256",
        "canonical_report_file_sha256",
        "binding_manifest_file_sha256",
        "source_graph_hash",
        "production_model_hash",
        "report_model_hash",
    }.issubset(VerifiedRunSnapshotBinding.__dataclass_fields__)
