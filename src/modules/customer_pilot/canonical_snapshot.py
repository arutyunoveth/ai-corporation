"""Fail-closed immutable publication of trusted frozen canonical bytes."""

from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import os
import re
import stat
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Iterator

from src.modules.procurement_analysis.canonical_persistence import (
    PersistedCanonicalOutputs,
    SOURCE_GRAPH_HASH_ALGORITHM,
    verify_canonical_bytes,
)
from src.tender_research.config import load_config

_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_PARTIAL = re.compile(r"^\.analysis\.partial\.[A-Za-z0-9_-]{8,128}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
MANIFEST_VERSION = "r8-canonical-binding-v1"
VERIFICATION_POLICY_VERSION = "r8-frozen-canonical-verifier-v1"
PATH_SCOPE = "data-root-relative"
EXACT_FILE_SET = [
    "requirements.json",
    "canonical_report.json",
    "canonical-binding.manifest.json",
]
_MANIFEST_KEYS = {
    "manifest_version",
    "verification_policy_version",
    "path_scope",
    "customer_id",
    "project_id",
    "procurement_case_id",
    "run_id",
    "registry_number",
    "source_analysis_run_id",
    "source_graph_hash",
    "source_graph_hash_algorithm",
    "production_model_hash",
    "report_model_hash",
    "requirements_relative_path",
    "requirements_file_sha256",
    "canonical_report_relative_path",
    "canonical_report_file_sha256",
    "exact_file_set",
    "created_at",
}


class CanonicalSnapshotError(RuntimeError):
    pass


class CanonicalSnapshotContractError(CanonicalSnapshotError):
    pass


class CanonicalSnapshotStorageError(CanonicalSnapshotError):
    pass


class CanonicalSnapshotConflictError(CanonicalSnapshotError):
    pass


@dataclass(frozen=True)
class PublishedCanonicalSnapshot:
    analysis_directory: Path
    requirements_path: Path
    canonical_report_path: Path
    binding_manifest_path: Path
    requirements_relative_path: str
    canonical_report_relative_path: str
    binding_manifest_relative_path: str
    requirements_file_sha256: str
    canonical_report_file_sha256: str
    binding_manifest_file_sha256: str
    source_graph_hash: str
    source_graph_hash_algorithm: str
    production_model_hash: str
    report_model_hash: str
    verification_policy_version: str
    created_at: str
    manifest: dict
    manifest_bytes: bytes
    idempotent: bool


def _lstat(path: Path) -> os.stat_result:
    try:
        return path.lstat()
    except OSError as exc:
        raise CanonicalSnapshotStorageError(
            f"Cannot inspect snapshot path: {path.name}"
        ) from exc


def _directory(path: Path) -> None:
    value = _lstat(path)
    if stat.S_ISLNK(value.st_mode) or not stat.S_ISDIR(value.st_mode):
        raise CanonicalSnapshotStorageError(
            "Customer snapshot namespace contains an unsafe filesystem object"
        )


def _regular(path: Path) -> None:
    value = _lstat(path)
    if stat.S_ISLNK(value.st_mode) or not stat.S_ISREG(value.st_mode):
        raise CanonicalSnapshotStorageError(
            "Customer snapshot contains an unsafe filesystem object"
        )


def _configured_root() -> Path:
    root = Path(load_config().data_dir)
    # Fail closed for every existing ancestor; resolve() is not a security check.
    chain: list[Path] = []
    cursor = root
    while True:
        chain.append(cursor)
        if cursor.parent == cursor:
            break
        cursor = cursor.parent
    for item in reversed(chain):
        if item.exists():
            _directory(item)
    if not root.exists():
        raise CanonicalSnapshotStorageError("Configured data directory does not exist")
    return root


def _safe_segment(value: str) -> str:
    if not isinstance(value, str) or not _SAFE.fullmatch(value):
        raise CanonicalSnapshotContractError("Unsafe customer snapshot identifier")
    return value


def _safe_namespace(*segments: str) -> Path:
    root = _configured_root()
    current = root
    for segment in ("customer-pilot", *(_safe_segment(value) for value in segments)):
        child = current / segment
        if child.exists():
            _directory(child)
        else:
            try:
                child.mkdir(mode=0o750)
            except FileExistsError:
                # Another publisher may have created this exact component;
                # validate it before use rather than following it blindly.
                _directory(child)
            except OSError as exc:
                raise CanonicalSnapshotStorageError(
                    "Cannot create customer snapshot namespace"
                ) from exc
            else:
                _directory(child)
        current = child
    return current


def _relative(*parts: str) -> str:
    return str(Path("customer-pilot").joinpath(*parts))


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _validate_bundle(value: object) -> PersistedCanonicalOutputs:
    if not isinstance(value, PersistedCanonicalOutputs):
        raise CanonicalSnapshotContractError("Verified canonical bundle is required")
    for content, digest in (
        (value.requirements_bytes, value.requirements_file_sha256),
        (value.canonical_report_bytes, value.canonical_report_file_sha256),
    ):
        if (
            not isinstance(content, bytes)
            or not content
            or not isinstance(digest, str)
            or _sha(content) != digest
        ):
            raise CanonicalSnapshotContractError(
                "Verified canonical bytes do not match identity"
            )
    if any(
        not isinstance(item, str) or not _HASH.fullmatch(item)
        for item in (
            value.source_graph_hash,
            value.production_model_hash,
            value.report_model_hash,
        )
    ):
        raise CanonicalSnapshotContractError(
            "Verified canonical identities are invalid"
        )
    if SOURCE_GRAPH_HASH_ALGORITHM != "sha256-json-c14n-v1":
        raise CanonicalSnapshotContractError("Unsupported source graph hash policy")
    return value


def _manifest_bytes(payload: dict) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _validate_manifest(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != _MANIFEST_KEYS:
        raise CanonicalSnapshotContractError("Snapshot manifest schema is invalid")
    if (
        value["manifest_version"] != MANIFEST_VERSION
        or value["verification_policy_version"] != VERIFICATION_POLICY_VERSION
        or value["path_scope"] != PATH_SCOPE
        or value["source_graph_hash_algorithm"] != SOURCE_GRAPH_HASH_ALGORITHM
        or value["exact_file_set"] != EXACT_FILE_SET
    ):
        raise CanonicalSnapshotContractError("Snapshot manifest policy is invalid")
    if any(
        not isinstance(value[key], str) or not _HASH.fullmatch(value[key])
        for key in (
            "source_graph_hash",
            "production_model_hash",
            "report_model_hash",
            "requirements_file_sha256",
            "canonical_report_file_sha256",
        )
    ):
        raise CanonicalSnapshotContractError("Snapshot manifest identities are invalid")
    try:
        parsed = datetime.fromisoformat(value["created_at"])
    except (TypeError, ValueError) as exc:
        raise CanonicalSnapshotContractError(
            "Snapshot manifest timestamp is invalid"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CanonicalSnapshotContractError(
            "Snapshot manifest timestamp is not timezone aware"
        )
    return value


def _read_regular(path: Path) -> bytes:
    _regular(path)
    try:
        return path.read_bytes()
    except OSError as exc:
        raise CanonicalSnapshotStorageError("Snapshot file is unreadable") from exc


def _fsync_file(path: Path) -> None:
    try:
        with path.open("rb") as handle:
            os.fsync(handle.fileno())
    except OSError as exc:
        raise CanonicalSnapshotStorageError("Cannot fsync snapshot file") from exc


def _fsync_dir(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        if exc.errno in {
            errno.EINVAL,
            errno.ENOTSUP,
        }:  # documented unsupported directory fsync
            return
        raise CanonicalSnapshotStorageError("Cannot fsync snapshot directory") from exc


@contextmanager
def _run_lock(run_root: Path) -> Iterator[None]:
    lock = run_root / ".analysis.lock"
    try:
        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(lock, flags, 0o600)
    except OSError as exc:
        raise CanonicalSnapshotStorageError(
            "Cannot open customer snapshot lock"
        ) from exc
    try:
        _regular(lock)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    except OSError as exc:
        raise CanonicalSnapshotStorageError("Cannot lock customer snapshot") from exc
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _safe_remove_tree(path: Path) -> None:
    _directory(path)
    for child in list(path.iterdir()):
        mode = _lstat(child).st_mode
        if stat.S_ISDIR(mode) or stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
            raise CanonicalSnapshotStorageError("Unsafe stale snapshot partial")
        try:
            child.unlink()
        except OSError as exc:
            raise CanonicalSnapshotStorageError(
                "Cannot clean stale snapshot partial"
            ) from exc
    try:
        path.rmdir()
    except OSError as exc:
        raise CanonicalSnapshotStorageError(
            "Cannot remove stale snapshot partial"
        ) from exc


def _cleanup_partials(run_root: Path) -> None:
    _directory(run_root)
    try:
        children = list(run_root.iterdir())
    except OSError as exc:
        raise CanonicalSnapshotStorageError(
            "Cannot inspect customer snapshot namespace"
        ) from exc
    for item in children:
        if item.name.startswith(".analysis.partial."):
            if not _PARTIAL.fullmatch(item.name):
                raise CanonicalSnapshotStorageError(
                    "Unsafe stale snapshot partial name"
                )
            _safe_remove_tree(item)


def _snapshot_from_existing(
    *,
    final: Path,
    expected: dict,
    verified: PersistedCanonicalOutputs,
    paths: tuple[str, str, str],
) -> PublishedCanonicalSnapshot:
    _directory(final)
    try:
        names = sorted(item.name for item in final.iterdir())
    except OSError as exc:
        raise CanonicalSnapshotStorageError(
            "Cannot inspect immutable snapshot"
        ) from exc
    if names != sorted(EXACT_FILE_SET):
        raise CanonicalSnapshotContractError("Immutable snapshot file set is invalid")
    req, report, manifest = (final / name for name in EXACT_FILE_SET)
    req_bytes, report_bytes, manifest_bytes = (
        _read_regular(req),
        _read_regular(report),
        _read_regular(manifest),
    )
    try:
        payload = _validate_manifest(json.loads(manifest_bytes))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanonicalSnapshotContractError(
            "Immutable snapshot manifest is malformed"
        ) from exc
    if (
        req_bytes != verified.requirements_bytes
        or report_bytes != verified.canonical_report_bytes
    ):
        raise CanonicalSnapshotConflictError(
            "Existing immutable analysis snapshot conflicts"
        )
    if any(payload.get(key) != value for key, value in expected.items()):
        raise CanonicalSnapshotConflictError(
            "Existing immutable analysis snapshot conflicts"
        )
    # Exact bytes are revalidated from the immutable publication, never working output.
    actual = verify_canonical_bytes(
        requirements_bytes=req_bytes, canonical_report_bytes=report_bytes
    )
    if (
        actual.source_graph_hash,
        actual.production_model_hash,
        actual.report_model_hash,
    ) != (
        verified.source_graph_hash,
        verified.production_model_hash,
        verified.report_model_hash,
    ):
        raise CanonicalSnapshotConflictError(
            "Existing immutable analysis snapshot identities conflict"
        )
    return PublishedCanonicalSnapshot(
        final,
        req,
        report,
        manifest,
        *paths,
        actual.requirements_file_sha256,
        actual.canonical_report_file_sha256,
        _sha(manifest_bytes),
        actual.source_graph_hash,
        SOURCE_GRAPH_HASH_ALGORITHM,
        actual.production_model_hash,
        actual.report_model_hash,
        VERIFICATION_POLICY_VERSION,
        payload["created_at"],
        payload,
        manifest_bytes,
        True,
    )


def publish_canonical_snapshot(
    *,
    customer_id: str,
    project_id: str,
    procurement_case_id: str,
    run_id: str,
    registry_number: str,
    source_analysis_run_id: str | None,
    verified: PersistedCanonicalOutputs,
    now_factory: Callable[[], datetime] = lambda: datetime.now(UTC),
    fault: Callable[[str], None] | None = None,
) -> PublishedCanonicalSnapshot:
    """Publish exactly one immutable generation for a customer run."""
    verified = _validate_bundle(verified)  # before any filesystem mutation
    segments = tuple(
        _safe_segment(value)
        for value in (customer_id, project_id, procurement_case_id, run_id)
    )
    if (
        not isinstance(registry_number, str)
        or not registry_number
        or not isinstance(source_analysis_run_id, str)
        or not source_analysis_run_id
    ):
        raise CanonicalSnapshotContractError("Snapshot ownership is invalid")
    run_root = _safe_namespace(*segments)
    base = _relative(*segments, "analysis")
    paths = (
        f"{base}/requirements.json",
        f"{base}/canonical_report.json",
        f"{base}/canonical-binding.manifest.json",
    )
    expected = {
        "customer_id": customer_id,
        "project_id": project_id,
        "procurement_case_id": procurement_case_id,
        "run_id": run_id,
        "registry_number": registry_number,
        "source_analysis_run_id": source_analysis_run_id,
        "source_graph_hash": verified.source_graph_hash,
        "source_graph_hash_algorithm": SOURCE_GRAPH_HASH_ALGORITHM,
        "production_model_hash": verified.production_model_hash,
        "report_model_hash": verified.report_model_hash,
        "requirements_relative_path": paths[0],
        "requirements_file_sha256": verified.requirements_file_sha256,
        "canonical_report_relative_path": paths[1],
        "canonical_report_file_sha256": verified.canonical_report_file_sha256,
    }
    final = run_root / "analysis"
    with _run_lock(run_root):
        if final.exists():
            return _snapshot_from_existing(
                final=final, expected=expected, verified=verified, paths=paths
            )
        _cleanup_partials(run_root)
        try:
            temp = Path(tempfile.mkdtemp(prefix=".analysis.partial.", dir=run_root))
        except OSError as exc:
            raise CanonicalSnapshotStorageError(
                "Cannot create snapshot staging directory"
            ) from exc
        if fault:
            fault("after_temp_created")
        payload = {
            "manifest_version": MANIFEST_VERSION,
            "verification_policy_version": VERIFICATION_POLICY_VERSION,
            "path_scope": PATH_SCOPE,
            **expected,
            "exact_file_set": EXACT_FILE_SET,
            "created_at": now_factory().astimezone(UTC).isoformat(),
        }
        manifest_bytes = _manifest_bytes(payload)
        try:
            for name, content, point in (
                (
                    "requirements.json",
                    verified.requirements_bytes,
                    "after_requirements_written",
                ),
                (
                    "canonical_report.json",
                    verified.canonical_report_bytes,
                    "after_canonical_written",
                ),
                (
                    "canonical-binding.manifest.json",
                    manifest_bytes,
                    "after_manifest_written",
                ),
            ):
                target = temp / name
                with target.open("xb") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                if fault:
                    fault(point)
            req_bytes, report_bytes, actual_manifest = (
                _read_regular(temp / "requirements.json"),
                _read_regular(temp / "canonical_report.json"),
                _read_regular(temp / "canonical-binding.manifest.json"),
            )
            if (req_bytes, report_bytes, actual_manifest) != (
                verified.requirements_bytes,
                verified.canonical_report_bytes,
                manifest_bytes,
            ):
                raise CanonicalSnapshotStorageError(
                    "Snapshot staging bytes changed during publication"
                )
            _validate_manifest(json.loads(actual_manifest))
            actual = verify_canonical_bytes(
                requirements_bytes=req_bytes, canonical_report_bytes=report_bytes
            )
            if (
                actual.source_graph_hash,
                actual.production_model_hash,
                actual.report_model_hash,
            ) != (
                verified.source_graph_hash,
                verified.production_model_hash,
                verified.report_model_hash,
            ):
                raise CanonicalSnapshotContractError(
                    "Snapshot staging canonical identities are invalid"
                )
            if sorted(item.name for item in temp.iterdir()) != sorted(EXACT_FILE_SET):
                raise CanonicalSnapshotContractError(
                    "Snapshot staging file set is invalid"
                )
            if fault:
                fault("before_temp_directory_fsync")
            _fsync_dir(temp)
            if fault:
                fault("before_rename")
            os.replace(temp, final)
            if fault:
                fault("after_rename")
            if fault:
                fault("before_parent_fsync")
            _fsync_dir(run_root)
        except CanonicalSnapshotError:
            if temp.exists():
                _safe_remove_tree(temp)
            raise
        except OSError as exc:
            if temp.exists():
                _safe_remove_tree(temp)
            raise CanonicalSnapshotStorageError(
                "Immutable snapshot publication failed"
            ) from exc
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            if temp.exists():
                _safe_remove_tree(temp)
            raise CanonicalSnapshotContractError(
                "Snapshot staging contract is invalid"
            ) from exc
    return PublishedCanonicalSnapshot(
        final,
        final / "requirements.json",
        final / "canonical_report.json",
        final / "canonical-binding.manifest.json",
        *paths,
        verified.requirements_file_sha256,
        verified.canonical_report_file_sha256,
        _sha(manifest_bytes),
        verified.source_graph_hash,
        SOURCE_GRAPH_HASH_ALGORITHM,
        verified.production_model_hash,
        verified.report_model_hash,
        VERIFICATION_POLICY_VERSION,
        payload["created_at"],
        payload,
        manifest_bytes,
        False,
    )
