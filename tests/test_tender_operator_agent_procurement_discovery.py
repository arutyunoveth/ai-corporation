def test_demo_local_procurement_search_returns_results(client):
    response = client.get(
        "/api/demo/tender-agent/procurements/search",
        params={"query": "электротехническое оборудование", "source": "demo_local", "max_results": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "demo_local"
    assert payload["results"]
    first = payload["results"][0]
    assert first["procurement_id"]
    assert first["title"]
    assert first["customer_name"] == "Промышленный заказчик"
    assert first["attachments_status"] in {
        "downloadable",
        "manual_upload_required",
        "unavailable_in_demo",
        "source_requires_authorization",
    }
    assert payload["sources"]


def test_unknown_procurement_source_is_rejected(client):
    response = client.get(
        "/api/demo/tender-agent/procurements/search",
        params={"query": "кабель", "source": "unknown_source"},
    )

    assert response.status_code == 400
    assert "Unknown procurement source" in response.json()["detail"]


def test_disabled_procurement_source_returns_warning(client):
    response = client.get(
        "/api/demo/tender-agent/procurements/search",
        params={"query": "кабель", "source": "mos_portal_public_api"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"] == []
    assert payload["warnings"]
