import json
import zipfile
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook


def _set_runs_root(monkeypatch, tmp_path: Path) -> Path:
    runs_root = tmp_path / "tender_operator_demo_runs"
    monkeypatch.setenv("AI_CORP_TENDER_OPERATOR_DEMO_RUNS_DIR", str(runs_root))
    return runs_root


def _sample_upload_payload(include_quote: bool = True):
    files = [
        ("files", ("notice.txt", b"NOTICE\nProcurement of electrical equipment for switchgear upgrade.", "text/plain")),
        ("files", ("technical_spec.txt", b"Technical specification. Delivery in 45 days. Certificates required.", "text/plain")),
        ("files", ("contract_draft.txt", b"Draft contract. Penalty for delay. Payment after acceptance.", "text/plain")),
    ]
    if include_quote:
        files.append(
            ("files", ("supplier_quote.txt", b"Supplier quote. Total price 11820000 RUB. Delivery 42 days.", "text/plain"))
        )
    data = {
        "tender_title": "Upload Demo Tender",
        "tender_category": "Электротехническое оборудование",
        "customer_name": "Промышленный заказчик",
        "notes": "Smoke upload run",
    }
    return data, files


def _build_quote_xlsx_bytes(*, supplier_label: str, english: bool = False) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Quote"
    if english:
        sheet.append(["Item", "Description", "Quantity", "Unit", "Unit Price", "Amount", "Delivery", "Currency"])
    else:
        sheet.append(["№", "Наименование", "Кол-во", "Ед. изм.", "Цена", "Сумма", "Срок поставки", "Валюта"])
    sheet.append([1, "Шкаф управления", 2, "шт", 120000, 240000, "35 дней", "RUB"])
    sheet.append([2, "Кабель силовой", 100, "м", 450, 45000, "35 дней", "RUB"])
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def _build_zip_bytes(entries: list[tuple[str, bytes]]) -> bytes:
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries:
            archive.writestr(name, content)
    return stream.getvalue()


def test_tender_operator_demo_page_shows_both_modes(client):
    response = client.get("/demo/tender-agent")

    assert response.status_code == 200
    assert "Demo dataset" in response.text
    assert "Upload &amp; Analyze" in response.text


def test_create_uploaded_run_with_txt_files(client, monkeypatch, tmp_path):
    runs_root = _set_runs_root(monkeypatch, tmp_path)
    data, files = _sample_upload_payload(include_quote=False)

    response = client.post("/api/demo/tender-agent/runs", data=data, files=files)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready_to_analyze"
    assert payload["file_count"] == 3

    metadata_path = runs_root / payload["run_id"] / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["mode"] == "uploaded_demo"
    assert metadata["human_in_the_loop"] is True
    assert metadata["external_actions"] is False
    assert metadata["no_platform_submission"] is True
    assert metadata["files"][0]["stored_name"].startswith("01-")
    assert metadata["economics_inputs"]["target_margin_percent"] == 15.0
    assert metadata["economics_inputs"]["payment_delay_days"] == 45


def test_path_traversal_filename_is_sanitized(client, monkeypatch, tmp_path):
    runs_root = _set_runs_root(monkeypatch, tmp_path)
    data, files = _sample_upload_payload(include_quote=False)
    files[0] = ("files", ("../../notice.txt", b"NOTICE\nSafe name only.", "text/plain"))

    response = client.post("/api/demo/tender-agent/runs", data=data, files=files)

    assert response.status_code == 200
    payload = response.json()
    metadata = json.loads((runs_root / payload["run_id"] / "metadata.json").read_text(encoding="utf-8"))
    stored_name = metadata["files"][0]["stored_name"]
    assert ".." not in stored_name
    assert "/" not in stored_name
    assert "\\" not in stored_name
    assert metadata["warnings"]


def test_unsupported_file_type_is_rejected(client, monkeypatch, tmp_path):
    _set_runs_root(monkeypatch, tmp_path)
    data = {
        "tender_title": "Unsafe",
        "tender_category": "Электротехническое оборудование",
        "customer_name": "Промышленный заказчик",
    }
    files = [("files", ("malware.exe", b"MZ", "application/octet-stream"))]

    response = client.post("/api/demo/tender-agent/runs", data=data, files=files)

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_analyze_uploaded_run_returns_completed_and_report_endpoints_work(client, monkeypatch, tmp_path):
    runs_root = _set_runs_root(monkeypatch, tmp_path)
    data, files = _sample_upload_payload(include_quote=True)

    create_response = client.post("/api/demo/tender-agent/runs", data=data, files=files)
    run_id = create_response.json()["run_id"]

    analyze = client.post(f"/api/demo/tender-agent/runs/{run_id}/analyze")
    assert analyze.status_code == 200
    analyze_payload = analyze.json()
    assert analyze_payload["status"] in {"completed", "completed_with_warnings"}
    assert analyze_payload["analysis_mode"] == "controlled_runner_adapter"

    run_response = client.get(f"/api/demo/tender-agent/runs/{run_id}")
    steps_response = client.get(f"/api/demo/tender-agent/runs/{run_id}/steps")
    report_response = client.get(f"/api/demo/tender-agent/runs/{run_id}/report")
    download_response = client.get(f"/api/demo/tender-agent/runs/{run_id}/report/download")
    report_page = client.get(f"/demo/tender-agent/runs/{run_id}/report")

    assert run_response.status_code == 200
    run_payload = run_response.json()
    assert run_payload["external_actions"] is False
    assert run_payload["human_in_the_loop"] is True
    assert run_payload["report_html_url"].endswith(f"/demo/tender-agent/runs/{run_id}/report")

    assert steps_response.status_code == 200
    steps_payload = steps_response.json()
    assert steps_payload["run_id"] == run_id
    assert len(steps_payload["steps"]) == 8
    assert {step["key"] for step in steps_payload["steps"]} == {
        "documents",
        "requirements",
        "questions",
        "rfq",
        "quotes",
        "economics",
        "risks",
        "decision",
    }

    assert report_response.status_code == 200
    assert report_response.json()["run_id"] == run_id

    assert download_response.status_code == 200
    assert download_response.headers["content-type"].startswith("text/html")
    assert "attachment; filename=" in download_response.headers["content-disposition"]
    assert report_page.status_code == 200
    assert "Tender Operator Uploaded Demo Report" in report_page.text

    assert (runs_root / run_id / "output" / "report.html").exists()


def test_analyze_without_quotes_stays_honest_and_needs_review(client, monkeypatch, tmp_path):
    _set_runs_root(monkeypatch, tmp_path)
    data, files = _sample_upload_payload(include_quote=False)

    create_response = client.post("/api/demo/tender-agent/runs", data=data, files=files)
    run_id = create_response.json()["run_id"]

    analyze = client.post(f"/api/demo/tender-agent/runs/{run_id}/analyze")
    assert analyze.status_code == 200
    analyze_payload = analyze.json()
    assert analyze_payload["status"] in {"needs_review", "completed_with_warnings"}
    assert analyze_payload["final_recommendation"]["recommendation"] == "manual_review_required"

    steps_payload = client.get(f"/api/demo/tender-agent/runs/{run_id}/steps").json()
    quotes_step = next(step for step in steps_payload["steps"] if step["key"] == "quotes")
    economics_step = next(step for step in steps_payload["steps"] if step["key"] == "economics")
    assert quotes_step["status"] == "blocked"
    assert economics_step["status"] == "blocked"


def test_fallback_mode_does_not_crash_when_pdf_extraction_is_unavailable(client, monkeypatch, tmp_path):
    _set_runs_root(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "src.modules.tender_operator_agent_demo.upload_service.extract_text_from_attachment_bytes",
        lambda **_kwargs: None,
    )
    data = {
        "tender_title": "PDF fallback demo",
        "tender_category": "Электротехническое оборудование",
        "customer_name": "Промышленный заказчик",
    }
    files = [
        ("files", ("notice.pdf", b"%PDF-1.4 fake", "application/pdf")),
        ("files", ("contract_draft.docx", b"PK\x03\x04fake", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
    ]

    create_response = client.post("/api/demo/tender-agent/runs", data=data, files=files)
    run_id = create_response.json()["run_id"]

    analyze = client.post(f"/api/demo/tender-agent/runs/{run_id}/analyze")

    assert analyze.status_code == 200
    payload = analyze.json()
    assert payload["analysis_mode"] == "fallback_deterministic_adapter"
    assert payload["status"] in {"needs_review", "completed_with_warnings"}


def test_xlsx_quotes_are_normalized_and_report_includes_quote_sections(client, monkeypatch, tmp_path):
    _set_runs_root(monkeypatch, tmp_path)
    data, files = _sample_upload_payload(include_quote=False)
    files.extend(
        [
            ("files", ("ТКП_ПоставщикА.xlsx", _build_quote_xlsx_bytes(supplier_label="Поставщик А"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
            ("files", ("quote_supplier_b.xlsx", _build_quote_xlsx_bytes(supplier_label="Supplier B", english=True), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
        ]
    )

    create_response = client.post("/api/demo/tender-agent/runs", data=data, files=files)
    run_id = create_response.json()["run_id"]

    analyze = client.post(f"/api/demo/tender-agent/runs/{run_id}/analyze")
    assert analyze.status_code == 200

    run_payload = client.get(f"/api/demo/tender-agent/runs/{run_id}").json()
    assert run_payload["quote_comparison"]["supplier_quotes_found"] >= 2
    assert run_payload["quote_comparison"]["items_extracted"] >= 2
    assert run_payload["economics_summary"]["economics_status"] in {"conditionally_viable", "insufficient_data"}
    assert run_payload["economics_summary"]["supplier_cost_selected"] is not None

    report_page = client.get(f"/demo/tender-agent/runs/{run_id}/report")
    assert report_page.status_code == 200
    assert "Supplier quote extraction" in report_page.text
    assert "Quote comparison" in report_page.text
    assert "Economics" in report_page.text


def test_zip_with_safe_xlsx_is_processed(client, monkeypatch, tmp_path):
    _set_runs_root(monkeypatch, tmp_path)
    data, files = _sample_upload_payload(include_quote=False)
    zip_payload = _build_zip_bytes(
        [("ТКП_ПоставщикА.xlsx", _build_quote_xlsx_bytes(supplier_label="Поставщик А"))]
    )
    files.append(("files", ("quotes_bundle.zip", zip_payload, "application/zip")))

    create_response = client.post("/api/demo/tender-agent/runs", data=data, files=files)
    run_id = create_response.json()["run_id"]
    analyze = client.post(f"/api/demo/tender-agent/runs/{run_id}/analyze")

    assert analyze.status_code == 200
    run_payload = client.get(f"/api/demo/tender-agent/runs/{run_id}").json()
    assert run_payload["quote_comparison"]["supplier_quotes_found"] >= 1


def test_zip_path_traversal_is_rejected_safely(client, monkeypatch, tmp_path):
    _set_runs_root(monkeypatch, tmp_path)
    data, files = _sample_upload_payload(include_quote=False)
    zip_payload = _build_zip_bytes(
        [
            ("../escape.xlsx", _build_quote_xlsx_bytes(supplier_label="Поставщик А")),
            ("safe/ТКП_ПоставщикБ.xlsx", _build_quote_xlsx_bytes(supplier_label="Поставщик Б")),
        ]
    )
    files.append(("files", ("quotes_bundle.zip", zip_payload, "application/zip")))

    create_response = client.post("/api/demo/tender-agent/runs", data=data, files=files)
    run_id = create_response.json()["run_id"]
    analyze = client.post(f"/api/demo/tender-agent/runs/{run_id}/analyze")

    assert analyze.status_code == 200
    run_payload = client.get(f"/api/demo/tender-agent/runs/{run_id}").json()
    assert any("unsafe path" in warning for warning in run_payload["warnings"])
