import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

from src.modules.customer_pilot import artifacts
from src.modules.customer_pilot.models import PilotProject, ProcurementCase
from src.modules.customer_pilot.router import StartIn, start_run
from src.modules.customer_registry.models import CustomerProfile
from src.shared.db.base import Base
from src.shared.api.middleware import _is_protected_path
from src.shared.config.settings import Settings
from src.tender_research.models import TenderAnalysisRun
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


def _customer(session, customer_id: str) -> None:
    session.add(
        CustomerProfile(
            customer_id=customer_id, legal_name=customer_id, customer_status="prospect"
        )
    )
    session.commit()


def _case(client, customer_id: str, name: str = "Pilot") -> dict:
    project = client.post(
        f"/api/operator/pilot/customers/{customer_id}/projects", json={"name": name}
    ).json()
    response = client.post(
        f"/api/operator/pilot/customers/{customer_id}/projects/{project['id']}/cases",
        json={"procurement_number": "0379100000726000101"},
    )
    assert response.status_code == 201
    return response.json()


def test_two_customers_are_isolated_and_same_procurement_has_distinct_keys(
    client, session
):
    _customer(session, "CUST-A")
    _customer(session, "CUST-B")
    case_a, case_b = _case(client, "CUST-A"), _case(client, "CUST-B")
    assert case_a["id"] != case_b["id"]
    assert case_a["artifact_key"] != case_b["artifact_key"]
    assert (
        client.get(
            f"/api/operator/pilot/customers/CUST-A/cases/{case_b['id']}"
        ).status_code
        == 404
    )


def _manifest_for_run(session, run_id, root, monkeypatch):
    run = session.get(TenderAnalysisRun, run_id)
    folder = root / "customer" / run.customer_id / run.project_id / run.id
    folder.mkdir(parents=True)
    pdf = folder / "final.pdf"
    pdf.write_bytes(b"%PDF-1.4\nR8 acceptance\n")
    manifest = {
        "run_id": run.id,
        "registry_number": run.registry_number,
        "artifact_key": run.artifact_key,
        "report_model_hash": "f" * 64,
        "renderer_version": "r7-persisted-pdf-v2",
        "pdf_relative_path": str(pdf.relative_to(root)),
        "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "byte_size": pdf.stat().st_size,
    }
    manifest_path = folder / "final.manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    run.metadata_json = json.dumps(
        {"artifact_manifest_path": str(manifest_path.relative_to(root))}
    )
    session.commit()
    monkeypatch.setattr(
        artifacts, "load_config", lambda: type("Config", (), {"data_dir": str(root)})()
    )
    return pdf


def test_idempotent_start_review_feedback_and_delivery_contract(
    client, session, tmp_path, monkeypatch
):
    _customer(session, "CUST-A")
    case = _case(client, "CUST-A")
    url = f"/api/operator/pilot/customers/CUST-A/cases/{case['id']}/runs"
    first = client.post(url, json={}, headers={"Idempotency-Key": "one"})
    again = client.post(url, json={}, headers={"Idempotency-Key": "one"})
    assert first.status_code == 201 and again.status_code == 201
    assert (
        again.json()["idempotent"] is True and first.json()["id"] == again.json()["id"]
    )
    run_id = first.json()["id"]
    assert (
        client.post(
            f"/api/operator/pilot/customers/CUST-A/cases/{case['id']}/runs/{run_id}/complete"
        ).status_code
        == 200
    )
    review = client.post(
        f"/api/operator/pilot/customers/CUST-A/cases/{case['id']}/runs/{run_id}/review",
        json={"reviewer": "operator", "verdict": "approved"},
    )
    assert review.status_code == 409
    _manifest_for_run(session, run_id, tmp_path, monkeypatch)
    review = client.post(
        f"/api/operator/pilot/customers/CUST-A/cases/{case['id']}/runs/{run_id}/review",
        json={"reviewer": "operator", "verdict": "approved"},
    )
    assert review.status_code == 200 and review.json()["immutable"] is True
    feedback = client.post(
        f"/api/operator/pilot/customers/CUST-A/cases/{case['id']}/feedback?run_id={run_id}",
        json={"category": "report_usability", "severity": "low", "comment": "ok"},
    )
    assert feedback.status_code == 201
    assert (
        client.post(
            f"/api/operator/pilot/customers/CUST-A/cases/{case['id']}/client-ready"
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/operator/pilot/customers/CUST-A/cases/{case['id']}/delivered"
        ).status_code
        == 200
    )


def test_cross_customer_run_and_feedback_are_not_disclosed(client, session):
    _customer(session, "CUST-A")
    _customer(session, "CUST-B")
    case_a, case_b = _case(client, "CUST-A"), _case(client, "CUST-B")
    run = client.post(
        f"/api/operator/pilot/customers/CUST-A/cases/{case_a['id']}/runs",
        json={},
        headers={"Idempotency-Key": "A"},
    ).json()
    response = client.post(
        f"/api/operator/pilot/customers/CUST-B/cases/{case_b['id']}/runs/{run['id']}/complete"
    )
    assert response.status_code == 404


def test_concurrent_different_keys_create_only_one_active_run(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'concurrent.db'}", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        customer = CustomerProfile(
            customer_id="CUST-RACE", legal_name="Race", customer_status="prospect"
        )
        project = PilotProject(
            customer_id=customer.customer_id, name="Race", internal_slug="race"
        )
        session.add_all([customer, project])
        session.flush()
        case = ProcurementCase(
            customer_id=customer.customer_id,
            project_id=project.id,
            procurement_number="0379100000726000101",
            artifact_key="c_race",
        )
        session.add(case)
        session.commit()
        case_id = case.id

    def attempt(key):
        with factory() as session:
            try:
                return start_run("CUST-RACE", case_id, StartIn(), session, key)
            except Exception as exc:
                return getattr(exc, "status_code", 500)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, ["key-a", "key-b"]))
    assert sum(isinstance(item, dict) for item in outcomes) == 1
    assert 409 in outcomes
    with factory() as session:
        runs = session.scalars(
            select(TenderAnalysisRun).where(
                TenderAnalysisRun.procurement_case_id == case_id
            )
        ).all()
        assert len(runs) == 1 and runs[0].status == "analyzing"


def test_customer_pilot_router_is_inside_existing_operator_auth_boundary():
    assert _is_protected_path("/api/operator/pilot/summary", ("/api",), ("/health",))
    assert "/api" in Settings().pilot_auth_protected_prefixes.split(",")
