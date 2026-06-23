import json
from pathlib import Path


def _set_runs_root(monkeypatch, tmp_path: Path) -> Path:
    runs_root = tmp_path / "tender_operator_demo_runs"
    monkeypatch.setenv("AI_CORP_TENDER_OPERATOR_DEMO_RUNS_DIR", str(runs_root))
    return runs_root


def test_create_run_from_demo_procurement_with_attachments_and_analyze(client, monkeypatch, tmp_path):
    runs_root = _set_runs_root(monkeypatch, tmp_path)

    create = client.post(
        "/api/demo/tender-agent/runs/from-procurement",
        json={
            "procurement_id": "DEMO-PR-001",
            "source": "demo_local",
            "query": "электротехническое оборудование",
        },
    )

    assert create.status_code == 200
    payload = create.json()
    assert payload["status"] == "ready_to_analyze"
    assert payload["file_count"] >= 3
    assert payload["downloaded_files_count"] == payload["file_count"]
    assert payload["manual_upload_required"] is False
    assert payload["run_url"].endswith(payload["run_id"])
    assert payload["report_url"].endswith(f"{payload['run_id']}/report")
    assert payload["attachments_status"] == "downloaded"

    metadata = json.loads((runs_root / payload["run_id"] / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["mode"] == "procurement_search_intake"
    assert metadata["procurement_source"] == "demo_local"
    assert metadata["procurement_id"] == "DEMO-PR-001"
    assert metadata["downloaded_files_count"] == payload["file_count"]
    assert metadata["manual_upload_required"] is False
    assert metadata["external_actions"] is False
    assert metadata["no_platform_submission"] is True
    assert metadata["no_email_sending"] is True
    assert metadata["no_digital_signature"] is True

    procurement_response = client.get(f"/api/demo/tender-agent/runs/{payload['run_id']}/procurement")
    assert procurement_response.status_code == 200
    procurement_payload = procurement_response.json()
    assert procurement_payload["procurement"]["procurement_id"] == "DEMO-PR-001"
    assert procurement_payload["attachments"]
    assert any(event["event_type"] == "run_created_from_procurement" for event in procurement_payload["events"])

    analyze = client.post(f"/api/demo/tender-agent/runs/{payload['run_id']}/analyze")
    assert analyze.status_code == 200
    analyze_payload = analyze.json()
    assert analyze_payload["status"] in {"completed", "completed_with_warnings", "needs_review"}

    run_payload = client.get(f"/api/demo/tender-agent/runs/{payload['run_id']}").json()
    assert run_payload["procurement_source"] == "demo_local"
    assert run_payload["procurement_id"] == "DEMO-PR-001"
    assert run_payload["attachments_status"] == "downloaded"
    assert any(step["key"] == "procurement_search" for step in run_payload["steps"])

    report_page = client.get(f"/demo/tender-agent/runs/{payload['run_id']}/report")
    assert report_page.status_code == 200
    assert "Поиск закупки и intake" in report_page.text


def test_create_run_from_procurement_without_attachments_becomes_docs_required(client, monkeypatch, tmp_path):
    _set_runs_root(monkeypatch, tmp_path)

    create = client.post(
        "/api/demo/tender-agent/runs/from-procurement",
        json={
            "procurement_id": "DEMO-PR-003",
            "source": "demo_local",
            "query": "шкаф управления",
        },
    )

    assert create.status_code == 200
    payload = create.json()
    assert payload["status"] == "docs_required"
    assert payload["attachments_status"] == "manual_upload_required"
    assert payload["downloaded_files_count"] == 0
    assert payload["manual_upload_required"] is True

    analyze = client.post(f"/api/demo/tender-agent/runs/{payload['run_id']}/analyze")
    assert analyze.status_code == 409


def test_manual_upload_to_procurement_run_enables_analysis(client, monkeypatch, tmp_path):
    _set_runs_root(monkeypatch, tmp_path)

    create = client.post(
        "/api/demo/tender-agent/runs/from-procurement",
        json={
            "procurement_id": "DEMO-PR-005",
            "source": "demo_local",
            "query": "электротехнические материалы",
        },
    )
    run_id = create.json()["run_id"]
    assert create.json()["status"] == "docs_required"

    files = [
        ("files", ("notice.txt", "Извещение. Поставка электротехнических материалов.".encode("utf-8"), "text/plain")),
        ("files", ("technical_spec.txt", "Техническое задание. Гарантия 12 месяцев.".encode("utf-8"), "text/plain")),
        ("files", ("contract_draft.txt", "Договор. Штрафы за просрочку.".encode("utf-8"), "text/plain")),
    ]
    upload = client.post(f"/api/demo/tender-agent/runs/{run_id}/files", files=files)
    assert upload.status_code == 200
    assert upload.json()["status"] == "ready_to_analyze"

    run_payload = client.get(f"/api/demo/tender-agent/runs/{run_id}").json()
    assert run_payload["attachments_status"] == "manual_upload_received"
    assert any(event["event_type"] == "manual_upload_received" for event in run_payload["events"])


def test_procurement_event_log_is_written(client, monkeypatch, tmp_path):
    runs_root = _set_runs_root(monkeypatch, tmp_path)

    create = client.post(
        "/api/demo/tender-agent/runs/from-procurement",
        json={
            "procurement_id": "DEMO-PR-002",
            "source": "demo_local",
            "query": "кабельная продукция",
        },
    )
    run_id = create.json()["run_id"]

    events_path = runs_root / run_id / "events.jsonl"
    assert events_path.exists()
    content = events_path.read_text(encoding="utf-8")
    assert "procurement_search_started" in content
    assert "run_created_from_procurement" in content


def test_procurement_intake_does_not_write_soap_token(client, monkeypatch, tmp_path):
    from src.modules.tender_operator_agent_demo.settings import clear_zakupki_soap_settings_cache

    runs_root = _set_runs_root(monkeypatch, tmp_path)
    token = "super-secret-token-for-local-test"
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_ENABLED", "1")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", token)
    clear_zakupki_soap_settings_cache()

    create = client.post(
        "/api/demo/tender-agent/runs/from-procurement",
        json={
            "procurement_id": "DEMO-PR-001",
            "source": "demo_local",
            "query": "электротехническое оборудование",
        },
    )

    assert create.status_code == 200
    run_dir = runs_root / create.json()["run_id"]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in run_dir.rglob("*.json*"))
    assert token not in combined
    clear_zakupki_soap_settings_cache()
