"""Neutral full verifier for an immutable customer canonical binding."""
from __future__ import annotations

from dataclasses import dataclass

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
    requirements_path: object
    canonical_report_path: object
    manifest_path: object
    snapshot: object


def verify_run_snapshot_binding(*, run, case, binding) -> VerifiedRunSnapshotBinding:
    """Verify DB ownership, exact manifest, exact file set and frozen bytes once."""
    if not binding.is_verified_snapshot_binding:
        raise RunSnapshotBindingContractError("Snapshot binding is structurally incomplete")
    if (binding.customer_id, binding.project_id, binding.procurement_case_id, binding.run_id) != (run.customer_id, run.project_id, case.id, run.id):
        raise RunSnapshotBindingConflictError("Snapshot binding ownership conflicts")
    try:
        snapshot = verify_customer_snapshot(
            customer_id=run.customer_id, project_id=run.project_id, procurement_case_id=case.id,
            run_id=run.id, registry_number=run.registry_number,
            source_analysis_run_id=binding.source_analysis_run_id,
            requirements_relative_path=binding.requirements_storage_key,
            canonical_report_relative_path=binding.canonical_report_storage_key,
            binding_manifest_relative_path=binding.binding_manifest_storage_key,
            binding_manifest_file_sha256=binding.binding_manifest_file_sha256,
            source_graph_hash=binding.source_graph_hash,
            production_model_hash=binding.production_model_hash,
            report_model_hash=binding.report_model_hash,
        )
        return VerifiedRunSnapshotBinding(
            snapshot.requirements_path.read_bytes(), snapshot.canonical_report_path.read_bytes(),
            snapshot.binding_manifest_path.read_bytes(), snapshot.requirements_path,
            snapshot.canonical_report_path, snapshot.binding_manifest_path, snapshot,
        )
    except CanonicalSnapshotContractError as exc:
        raise RunSnapshotBindingContractError(str(exc)) from exc
    except CanonicalSnapshotStorageError as exc:
        raise RunSnapshotBindingStorageError(str(exc)) from exc
    except (CanonicalSnapshotConflictError, CanonicalSnapshotError) as exc:
        raise RunSnapshotBindingConflictError(str(exc)) from exc
