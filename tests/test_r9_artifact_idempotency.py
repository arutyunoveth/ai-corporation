import hashlib

from sqlalchemy import func, select

from src.modules.customer_pilot import artifact_publisher, artifacts, canonical_snapshot
from src.modules.customer_pilot.models import (
    PilotArtifact,
    PilotAuditEvent,
    PilotRunResult,
)
from tests.test_r8_customer_pilot import _case, _customer, _trusted_analysis


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
    assert first.status_code == 201 and calls["count"] == 1
    responses = [first, *(client.post(endpoint) for _ in range(3))]
    assert all(response.status_code == 201 for response in responses)
    assert len({response.json()["id"] for response in responses}) == 1
    artifact = session.scalar(select(PilotArtifact))
    assert artifact is not None
    pdf_path, manifest_path = (
        tmp_path / artifact.pdf_relative_path,
        tmp_path / artifact.manifest_relative_path,
    )
    before = (
        hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        pdf_path.stat().st_mtime_ns,
        hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        manifest_path.stat().st_mtime_ns,
    )
    assert session.scalar(select(func.count()).select_from(PilotArtifact)) == 1
    assert session.scalar(select(func.count()).select_from(PilotRunResult)) == 1
    assert (
        session.scalar(
            select(func.count())
            .select_from(PilotAuditEvent)
            .where(PilotAuditEvent.event_type == "artifact_exported")
        )
        == 1
    )
    assert calls["count"] == 1
    assert {path.name for path in pdf_path.parent.iterdir()} == {
        "final.pdf",
        "artifact.manifest.json",
    }
    assert (
        hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        pdf_path.stat().st_mtime_ns,
        hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        manifest_path.stat().st_mtime_ns,
    ) == before


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
    endpoint = f"{base}/{run['id']}/artifacts/final-pdf"
    assert client.post(endpoint).status_code == 201
    artifact = session.scalar(select(PilotArtifact))
    pdf = tmp_path / artifact.pdf_relative_path
    pdf.write_bytes(b"tampered")
    assert client.post(endpoint).status_code == 409
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
