"""Neutral full verifier for an immutable customer canonical binding."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from src.modules.customer_pilot.canonical_snapshot import (
    CanonicalSnapshotConflictError,
    CanonicalSnapshotContractError,
    CanonicalSnapshotError,
    CanonicalSnapshotStorageError,
    verify_customer_snapshot,
)


class RunSnapshotBindingError(RuntimeError):
    pass


class RunSnapshotBindingContractError(RunSnapshotBindingError):
    pass


class RunSnapshotBindingStorageError(RunSnapshotBindingError):
    pass


class RunSnapshotBindingConflictError(RunSnapshotBindingError):
    pass


@dataclass(frozen=True)
class VerifiedRunSnapshotBinding:
    requirements_bytes: bytes
    canonical_report_bytes: bytes
    manifest_bytes: bytes
    parsed_requirements: dict
    parsed_canonical_report: dict
    parsed_manifest: dict
    requirements_path: Path
    canonical_report_path: Path
    manifest_path: Path
    requirements_file_sha256: str
    canonical_report_file_sha256: str
    binding_manifest_file_sha256: str
    source_graph_hash: str
    source_graph_hash_algorithm: str
    production_model_hash: str
    report_model_hash: str
    verification_policy_version: str
    source_analysis_run_id: str


def verify_run_snapshot_binding(*, run, case, binding) -> VerifiedRunSnapshotBinding:
    """Verify DB ownership, exact manifest, exact file set and frozen bytes once."""
    if not binding.is_verified_snapshot_binding:
        raise RunSnapshotBindingContractError(
            "Snapshot binding is structurally incomplete"
        )
    if (
        binding.customer_id,
        binding.project_id,
        binding.procurement_case_id,
        binding.run_id,
    ) != (run.customer_id, run.project_id, case.id, run.id):
        raise RunSnapshotBindingConflictError("Snapshot binding ownership conflicts")
    try:
        snapshot = verify_customer_snapshot(
            customer_id=run.customer_id,
            project_id=run.project_id,
            procurement_case_id=case.id,
            run_id=run.id,
            registry_number=run.registry_number,
            source_analysis_run_id=binding.source_analysis_run_id,
            requirements_relative_path=binding.requirements_storage_key,
            canonical_report_relative_path=binding.canonical_report_storage_key,
            binding_manifest_relative_path=binding.binding_manifest_storage_key,
            binding_manifest_file_sha256=binding.binding_manifest_file_sha256,
            requirements_file_sha256=binding.requirements_file_sha256,
            canonical_report_file_sha256=binding.canonical_report_file_sha256,
            source_graph_hash=binding.source_graph_hash,
            source_graph_hash_algorithm=binding.source_graph_hash_algorithm,
            production_model_hash=binding.production_model_hash,
            report_model_hash=binding.report_model_hash,
            verification_policy_version=binding.verification_policy_version,
        )
        return VerifiedRunSnapshotBinding(
            snapshot.requirements_bytes,
            snapshot.canonical_report_bytes,
            snapshot.manifest_bytes,
            json.loads(snapshot.requirements_bytes),
            json.loads(snapshot.canonical_report_bytes),
            snapshot.manifest,
            snapshot.requirements_path,
            snapshot.canonical_report_path,
            snapshot.binding_manifest_path,
            snapshot.requirements_file_sha256,
            snapshot.canonical_report_file_sha256,
            snapshot.binding_manifest_file_sha256,
            snapshot.source_graph_hash,
            snapshot.source_graph_hash_algorithm,
            snapshot.production_model_hash,
            snapshot.report_model_hash,
            snapshot.verification_policy_version,
            binding.source_analysis_run_id,
        )
    except CanonicalSnapshotContractError as exc:
        raise RunSnapshotBindingContractError(str(exc)) from exc
    except CanonicalSnapshotStorageError as exc:
        raise RunSnapshotBindingStorageError(str(exc)) from exc
    except (CanonicalSnapshotConflictError, CanonicalSnapshotError) as exc:
        raise RunSnapshotBindingConflictError(str(exc)) from exc
