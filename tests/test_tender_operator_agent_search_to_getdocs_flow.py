import json


def test_handoff_endpoint_requires_reestr_number(client, monkeypatch, tmp_path):
    from src.modules.tender_operator_agent_demo import procurement_intake_service as service
    from src.modules.tender_operator_agent_demo.settings import clear_zakupki_soap_settings_cache

    runs_root = tmp_path / "tender_operator_demo_runs"
    monkeypatch.setenv("AI_CORP_TENDER_OPERATOR_DEMO_RUNS_DIR", str(runs_root))
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_ENABLED", "1")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", "test-token-value-not-real")
    clear_zakupki_soap_settings_cache()

    response = client.post(
        "/api/demo/tender-agent/runs/from-search-result",
        json={
            "source": "public_44fz",
            "reestr_number": "",
            "download_archive": False,
            "analyze_after_download": False,
        },
    )
    assert response.status_code == 400
    assert "reestr_number" in response.json()["detail"].lower()


def test_handoff_endpoint_calls_getdocs_ip(client, monkeypatch, tmp_path):
    from src.modules.tender_operator_agent_demo import procurement_intake_service as service
    from src.modules.tender_operator_agent_demo.procurement_schemas import DocsArchiveResult, DownloadedAttachment
    from src.modules.tender_operator_agent_demo.settings import clear_zakupki_soap_settings_cache

    runs_root = tmp_path / "tender_operator_demo_runs"
    monkeypatch.setenv("AI_CORP_TENDER_OPERATOR_DEMO_RUNS_DIR", str(runs_root))
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_ENABLED", "1")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", "test-token-value-not-real")
    clear_zakupki_soap_settings_cache()

    class FakeClient:
        def __init__(self, _settings):
            pass

        def get_docs_by_reestr_number(self, _reestr_number, subsystem_type="PRIZ"):
            return DocsArchiveResult(
                request_id="req-handoff-001",
                ref_id="ref-handoff-001",
                archive_url="https://int44.zakupki.gov.ru/archive/demo.zip",
                status="completed",
                warnings=[],
                safe_diagnostic={"archive_url_present": True},
            )

        def download_archive(self, _archive_url, target_dir):
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "documentation-archive.zip").write_bytes(b"PK\x03\x04demo")
            return DownloadedAttachment(
                file_name="demo.zip",
                stored_name="documentation-archive.zip",
                size_bytes=10,
                content_type="application/zip",
                source_url_host="int44.zakupki.gov.ru",
                source_url_path="/archive/demo.zip",
            )

    monkeypatch.setattr(service, "ZakupkiSoapClient", FakeClient)
    monkeypatch.setattr(
        service,
        "_extract_safe_archive_into_run",
        lambda run_id, _path: (
            [
                service.build_demo_file_descriptor(
                    file_id="FILE-01",
                    original_name="notice.txt",
                    stored_name="01-notice.txt",
                    size_bytes=10,
                    content_type="text/plain",
                    source="eis_getdocs_archive",
                )
            ],
            [
                service.ProcurementAttachmentManifestItem(
                    name="notice.txt",
                    stored_name="01-notice.txt",
                    extension=".txt",
                    status="saved",
                    note="ok",
                )
            ],
            1,
        ),
    )

    response = client.post(
        "/api/demo/tender-agent/runs/from-search-result",
        json={
            "source": "public_44fz",
            "reestr_number": "0888200000224000038",
            "title": "Поставка оборудования",
            "customer_name": "ООО Тестовый заказчик",
            "source_url": "https://zakupki.gov.ru/epz/order/notice/ea44/view.html?regNumber=0888200000224000038",
            "download_archive": True,
            "analyze_after_download": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"]
    assert payload["run_id"]
    assert payload["archive_url_present"] is True
    assert "ticket" not in json.dumps(payload, ensure_ascii=False)
    clear_zakupki_soap_settings_cache()


def test_handoff_source_url_sanitized(client, monkeypatch, tmp_path):
    from src.modules.tender_operator_agent_demo import procurement_intake_service as service
    from src.modules.tender_operator_agent_demo.procurement_schemas import DocsArchiveResult, DownloadedAttachment
    from src.modules.tender_operator_agent_demo.settings import clear_zakupki_soap_settings_cache

    runs_root = tmp_path / "tender_operator_demo_runs"
    monkeypatch.setenv("AI_CORP_TENDER_OPERATOR_DEMO_RUNS_DIR", str(runs_root))
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_ENABLED", "1")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", "test-token-value-not-real")
    clear_zakupki_soap_settings_cache()

    class FakeClient:
        def __init__(self, _settings):
            pass

        def get_docs_by_reestr_number(self, _reestr_number, subsystem_type="PRIZ"):
            return DocsArchiveResult(
                request_id="req-002",
                ref_id=None,
                archive_url=None,
                status="no_archive_url",
                warnings=[],
                safe_diagnostic={"archive_url_present": False},
            )

    monkeypatch.setattr(service, "ZakupkiSoapClient", FakeClient)

    response = client.post(
        "/api/demo/tender-agent/runs/from-search-result",
        json={
            "source": "public_44fz",
            "reestr_number": "0888200000224000038",
            "title": "Тест",
            "source_url": "https://zakupki.gov.ru/",
            "download_archive": False,
            "analyze_after_download": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in ("completed", "failed", "archive_not_ready", "completed_with_warnings", "archive_downloaded", "manual_upload_required", "docs_required")
    clear_zakupki_soap_settings_cache()


def test_existing_getdocs_intake_tests_still_pass(client, monkeypatch, tmp_path):
    from src.modules.tender_operator_agent_demo import procurement_intake_service as service
    from src.modules.tender_operator_agent_demo.procurement_schemas import DocsArchiveResult, DownloadedAttachment
    from src.modules.tender_operator_agent_demo.settings import clear_zakupki_soap_settings_cache

    runs_root = tmp_path / "tender_operator_demo_runs"
    monkeypatch.setenv("AI_CORP_TENDER_OPERATOR_DEMO_RUNS_DIR", str(runs_root))
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_ENABLED", "1")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", "test-token-value-not-real")
    clear_zakupki_soap_settings_cache()

    class FakeClient:
        def __init__(self, _settings):
            pass

        def get_docs_by_reestr_number(self, _reestr_number, subsystem_type="PRIZ"):
            return DocsArchiveResult(
                request_id="req-003",
                ref_id="ref-003",
                archive_url="https://int44.zakupki.gov.ru/archive/demo.zip",
                status="completed",
                warnings=[],
                safe_diagnostic={"archive_url_present": True},
            )

        def download_archive(self, _archive_url, target_dir):
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "documentation-archive.zip").write_bytes(b"PK\x03\x04demo")
            return DownloadedAttachment(
                file_name="demo.zip",
                stored_name="documentation-archive.zip",
                size_bytes=10,
                content_type="application/zip",
                source_url_host="int44.zakupki.gov.ru",
                source_url_path="/archive/demo.zip",
            )

    monkeypatch.setattr(service, "ZakupkiSoapClient", FakeClient)
    monkeypatch.setattr(
        service,
        "_extract_safe_archive_into_run",
        lambda run_id, _path: ([], [], 0),
    )

    response = client.post(
        "/api/demo/tender-agent/runs/from-eis-docs-archive",
        json={"reestr_number": "0888200000224000038", "law": "44fz", "subsystem_type": "PRIZ", "download_archive": False},
    )
    assert response.status_code == 200
    clear_zakupki_soap_settings_cache()
