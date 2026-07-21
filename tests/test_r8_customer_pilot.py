from src.modules.customer_registry.models import CustomerProfile


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


def test_idempotent_start_review_feedback_and_delivery_contract(client, session):
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
        json={
            "reviewer": "operator",
            "verdict": "approved",
            "artifact_hashes": {"pdf": "abc"},
        },
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
