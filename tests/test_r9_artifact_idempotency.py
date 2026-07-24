import hashlib
from datetime import datetime

from sqlalchemy import func, select

from src.modules.customer_pilot import artifact_publisher, artifacts, canonical_snapshot
from src.modules.customer_pilot.models import (
    PilotArtifact,
    PilotAuditEvent,
    PilotRunResult,
)
from tests.test_r8_customer_pilot import _case, _customer, _trusted_analysis


def _normalized_publication_response(response: dict) -> dict:
    normalized = response.copy()
    for field in ("created_at", "immutable_at"):
        if normalized.get(field) is not None:
            normalized[field] = (
                datetime.fromisoformat(normalized[field])
                .replace(tzinfo=None)
                .isoformat()
            )
    return normalized


def test_sequential_final_pdf_replays_are_side_effect_free(
    client, session, tmp_path, monkeypatch
):
    _customer(session, "R9-IDEMPOTENT")
    _trusted_analysis(monkeypatch, tmp_path, session)
    monkeypatch.setattr(
        artifacts,
        "load_config",
        lambda: type("Config", (), {"data_dir": str(tmp_path)})(),
    )
    monkeypatch.setattr(
        canonical_snapshot,
        "load_config",
        lambda: type("Config", (), {"data_dir": str(tmp_path)})(),
    )
    monkeypatch.setattr(
        artifact_publisher,
        "load_config",
        lambda: type("Config", (), {"data_dir": str(tmp_path)})(),
    )
    case = _case(client, "R9-IDEMPOTENT")
    base = f"/api/operator/pilot/customers/R9-IDEMPOTENT/cases/{case['id']}/runs"
    run = client.post(
        base, json={}, headers={"Idempotency-Key": "r9-idempotent"}
    ).json()
    assert client.post(f"{base}/{run['id']}/complete").status_code == 200
    from src.modules.tender_operator_agent_demo import report_export_service

    calls = {"count": 0}
    original = report_export_service._build_pdf_from_canonical

    def counted(*args, **kwargs):
        calls["count"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(report_export_service, "_build_pdf_from_canonical", counted)
    endpoint = f"{base}/{run['id']}/artifacts/final-pdf"
    first = client.post(endpoint)
    assert first.status_code == 201
    first_response = _normalized_publication_response(first.json())
    assert calls["count"] == 1
    artifact = session.scalar(select(PilotArtifact))
    assert artifact is not None
    pdf_path, manifest_path = (
        tmp_path / artifact.pdf_relative_path,
        tmp_path / artifact.manifest_relative_path,
    )
    baseline = {
        "response": first_response,
        "renderer_count": calls["count"],
        "pdf_sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        "pdf_mtime_ns": pdf_path.stat().st_mtime_ns,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "manifest_mtime_ns": manifest_path.stat().st_mtime_ns,
        "generation_entries": {path.name for path in pdf_path.parent.iterdir()},
        "artifact_count": session.scalar(
            select(func.count()).select_from(PilotArtifact)
        ),
        "run_result_count": session.scalar(
            select(func.count()).select_from(PilotRunResult)
        ),
        "export_audit_count": session.scalar(
            select(func.count())
            .select_from(PilotAuditEvent)
            .where(PilotAuditEvent.event_type == "artifact_exported")
        ),
    }
    assert baseline["artifact_count"] == 1
    assert baseline["run_result_count"] == 1
    assert baseline["export_audit_count"] == 1
    assert baseline["generation_entries"] == {"final.pdf", "artifact.manifest.json"}

    for _ in range(3):
        replay = client.post(endpoint)
        assert replay.status_code == 201
        assert _normalized_publication_response(replay.json()) == baseline["response"]
        assert calls["count"] == baseline["renderer_count"] == 1
        assert (
            hashlib.sha256(pdf_path.read_bytes()).hexdigest() == baseline["pdf_sha256"]
        )
        assert pdf_path.stat().st_mtime_ns == baseline["pdf_mtime_ns"]
        assert (
            hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            == baseline["manifest_sha256"]
        )
        assert manifest_path.stat().st_mtime_ns == baseline["manifest_mtime_ns"]
        assert {path.name for path in pdf_path.parent.iterdir()} == baseline[
            "generation_entries"
        ]
        assert (
            session.scalar(select(func.count()).select_from(PilotArtifact))
            == baseline["artifact_count"]
        )
        assert (
            session.scalar(select(func.count()).select_from(PilotRunResult))
            == baseline["run_result_count"]
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(PilotAuditEvent)
                .where(PilotAuditEvent.event_type == "artifact_exported")
            )
            == baseline["export_audit_count"]
        )


def test_tampered_existing_artifact_replay_fails_closed(
    client, session, tmp_path, monkeypatch
):
    _customer(session, "R9-TAMPER")
    _trusted_analysis(monkeypatch, tmp_path, session)
    config = lambda: type("Config", (), {"data_dir": str(tmp_path)})()
    monkeypatch.setattr(artifact_publisher, "load_config", config)
    monkeypatch.setattr(artifacts, "load_config", config)
    monkeypatch.setattr(canonical_snapshot, "load_config", config)
    case = _case(client, "R9-TAMPER")
    base = f"/api/operator/pilot/customers/R9-TAMPER/cases/{case['id']}/runs"
    run = client.post(base, json={}, headers={"Idempotency-Key": "r9-tamper"}).json()
    assert client.post(f"{base}/{run['id']}/complete").status_code == 200
    from src.modules.tender_operator_agent_demo import report_export_service

    calls = {"count": 0}
    original = report_export_service._build_pdf_from_canonical

    def counted(*args, **kwargs):
        calls["count"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(report_export_service, "_build_pdf_from_canonical", counted)
    endpoint = f"{base}/{run['id']}/artifacts/final-pdf"
    assert client.post(endpoint).status_code == 201
    assert calls["count"] == 1
    artifact = session.scalar(select(PilotArtifact))
    pdf = tmp_path / artifact.pdf_relative_path
    pdf.write_bytes(b"tampered")
    assert client.post(endpoint).status_code == 409
    assert calls["count"] == 1
    assert pdf.read_bytes() == b"tampered"
    assert session.scalar(select(func.count()).select_from(PilotArtifact)) == 1
    assert (
        session.scalar(
            select(func.count())
            .select_from(PilotAuditEvent)
            .where(PilotAuditEvent.event_type == "artifact_exported")
        )
        == 1
    )


def test_deterministic_filesystem_only_generation_is_not_rebound(
    client, session, tmp_path, monkeypatch
):
    _customer(session, "R9-ARTIFACT-ORPHAN")
    _trusted_analysis(monkeypatch, tmp_path, session)
    config = lambda: type("Config", (), {"data_dir": str(tmp_path)})()
    monkeypatch.setattr(artifact_publisher, "load_config", config)
    monkeypatch.setattr(artifacts, "load_config", config)
    monkeypatch.setattr(canonical_snapshot, "load_config", config)
    case = _case(client, "R9-ARTIFACT-ORPHAN")
    base = (
        f"/api/operator/pilot/customers/R9-ARTIFACT-ORPHAN/"
        f"cases/{case['id']}/runs"
    )
    run = client.post(
        base, json={}, headers={"Idempotency-Key": "r9-artifact-orphan"}
    ).json()
    assert client.post(f"{base}/{run['id']}/complete").status_code == 200

    from src.modules.tender_operator_agent_demo import report_export_service

    candidate = b"%PDF-1.4\nR9-DETERMINISTIC-ORPHAN\n%%EOF\n"
    calls = {"count": 0}

    def deterministic(_canonical, _title, output):
        calls["count"] += 1
        output.write_bytes(candidate)

    monkeypatch.setattr(
        report_export_service, "_build_pdf_from_canonical", deterministic
    )
    endpoint = f"{base}/{run['id']}/artifacts/final-pdf"
    first = client.post(endpoint)
    assert first.status_code == 201
    artifact = session.scalar(select(PilotArtifact))
    assert artifact is not None
    pdf_path = tmp_path / artifact.pdf_relative_path
    manifest_path = tmp_path / artifact.manifest_relative_path
    baseline = {
        "pdf_sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        "pdf_mtime_ns": pdf_path.stat().st_mtime_ns,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "manifest_mtime_ns": manifest_path.stat().st_mtime_ns,
        "audit_count": session.scalar(
            select(func.count())
            .select_from(PilotAuditEvent)
            .where(PilotAuditEvent.event_type == "artifact_exported")
        ),
    }
    session.delete(artifact)
    session.commit()
    assert session.scalar(select(func.count()).select_from(PilotArtifact)) == 0

    retry = client.post(endpoint)
    assert retry.status_code == 409
    assert retry.json() == {"detail": "Final PDF generation exists without DB binding"}
    session.expire_all()
    assert calls["count"] == 2
    assert session.scalar(select(func.count()).select_from(PilotArtifact)) == 0
    assert (
        session.scalar(
            select(func.count())
            .select_from(PilotAuditEvent)
            .where(PilotAuditEvent.event_type == "artifact_exported")
        )
        == baseline["audit_count"]
    )
    assert hashlib.sha256(pdf_path.read_bytes()).hexdigest() == baseline["pdf_sha256"]
    assert pdf_path.stat().st_mtime_ns == baseline["pdf_mtime_ns"]
    assert (
        hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        == baseline["manifest_sha256"]
    )
    assert manifest_path.stat().st_mtime_ns == baseline["manifest_mtime_ns"]
