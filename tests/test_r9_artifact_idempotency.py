from sqlalchemy import func, select

from src.modules.customer_pilot import artifact_publisher, artifacts, canonical_snapshot
from src.modules.customer_pilot.models import PilotArtifact, PilotAuditEvent, PilotRunResult
from tests.test_r8_customer_pilot import _case, _customer, _trusted_analysis


def test_sequential_final_pdf_replays_are_side_effect_free(client, session, tmp_path, monkeypatch):
    _customer(session, "R9-IDEMPOTENT")
    _trusted_analysis(monkeypatch, tmp_path, session)
    monkeypatch.setattr(artifacts, "load_config", lambda: type("Config", (), {"data_dir": str(tmp_path)})())
    monkeypatch.setattr(canonical_snapshot, "load_config", lambda: type("Config", (), {"data_dir": str(tmp_path)})())
    monkeypatch.setattr(artifact_publisher, "load_config", lambda: type("Config", (), {"data_dir": str(tmp_path)})())
    case = _case(client, "R9-IDEMPOTENT")
    base = f"/api/operator/pilot/customers/R9-IDEMPOTENT/cases/{case['id']}/runs"
    run = client.post(base, json={}, headers={"Idempotency-Key": "r9-idempotent"}).json()
    assert client.post(f"{base}/{run['id']}/complete").status_code == 200
    endpoint = f"{base}/{run['id']}/artifacts/final-pdf"
    responses = [client.post(endpoint) for _ in range(4)]
    assert all(response.status_code == 201 for response in responses)
    assert len({response.json()["id"] for response in responses}) == 1
    artifact = session.scalar(select(PilotArtifact))
    assert artifact is not None
    before = ((tmp_path / artifact.pdf_relative_path).stat().st_mtime_ns, (tmp_path / artifact.manifest_relative_path).stat().st_mtime_ns)
    assert session.scalar(select(func.count()).select_from(PilotArtifact)) == 1
    assert session.scalar(select(func.count()).select_from(PilotRunResult)) == 1
    assert session.scalar(select(func.count()).select_from(PilotAuditEvent).where(PilotAuditEvent.event_type == "artifact_exported")) == 1
    assert [client.post(endpoint).json()["id"] for _ in range(3)] == [artifact.id] * 3
    assert ((tmp_path / artifact.pdf_relative_path).stat().st_mtime_ns, (tmp_path / artifact.manifest_relative_path).stat().st_mtime_ns) == before
