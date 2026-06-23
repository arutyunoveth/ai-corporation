import json
from pathlib import Path


def _set_runs_root(monkeypatch, tmp_path: Path) -> Path:
    runs_root = tmp_path / "tender_operator_demo_runs"
    monkeypatch.setenv("AI_CORP_TENDER_OPERATOR_DEMO_RUNS_DIR", str(runs_root))
    return runs_root


def test_getdocs_archive_endpoint_creates_run_with_archive_metadata(client, monkeypatch, tmp_path):
    from src.modules.tender_operator_agent_demo import procurement_intake_service as service
    from src.modules.tender_operator_agent_demo.procurement_schemas import DocsArchiveResult, DownloadedAttachment
    from src.modules.tender_operator_agent_demo.settings import clear_zakupki_soap_settings_cache

    runs_root = _set_runs_root(monkeypatch, tmp_path)
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_ENABLED", "1")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", "test-token-value-not-real")
    clear_zakupki_soap_settings_cache()

    class FakeClient:
        def __init__(self, _settings):
            pass

        def get_docs_by_reestr_number(self, _reestr_number, subsystem_type="PRIZ"):
            return DocsArchiveResult(
                request_id="req-001",
                ref_id="ref-001",
                archive_url="https://int44.zakupki.gov.ru/archive/demo.zip",
                status="completed",
                warnings=[],
                safe_diagnostic={"archive_url_present": True},
            )

        def download_archive(self, _archive_url, target_dir):
            payload = b"PK\x03\x04demo"
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "documentation-archive.zip").write_bytes(payload)
            return DownloadedAttachment(
                file_name="demo.zip",
                stored_name="documentation-archive.zip",
                size_bytes=len(payload),
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
        "/api/demo/tender-agent/runs/from-eis-docs-archive",
        json={"reestr_number": "0888200000224000038", "law": "44fz", "subsystem_type": "PRIZ", "download_archive": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready_to_analyze"
    assert payload["attachments_status"] == "downloaded"
    metadata = json.loads((runs_root / payload["run_id"] / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["source"] == "zakupki_gov_ru_getdocs_ip"
    assert metadata["token_owner"] == "individual"
    assert metadata["archive_url_present"] is True
    assert metadata["archive_downloaded"] is True
    assert metadata["documents_extracted_count"] == 1
    clear_zakupki_soap_settings_cache()


def test_getdocs_archive_endpoint_falls_back_to_manual_upload(client, monkeypatch, tmp_path):
    from src.modules.tender_operator_agent_demo import procurement_intake_service as service
    from src.modules.tender_operator_agent_demo.procurement_schemas import DocsArchiveResult
    from src.modules.tender_operator_agent_demo.settings import clear_zakupki_soap_settings_cache

    _set_runs_root(monkeypatch, tmp_path)
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
                warnings=["archiveUrl not found"],
                safe_diagnostic={"archive_url_present": False},
            )

    monkeypatch.setattr(service, "ZakupkiSoapClient", FakeClient)

    response = client.post(
        "/api/demo/tender-agent/runs/from-eis-docs-archive",
        json={"reestr_number": "0888200000224000038", "law": "44fz", "subsystem_type": "PRIZ", "download_archive": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "docs_required"
    assert payload["manual_upload_required"] is True
    assert payload["attachments_status"] == "manual_upload_required"
    clear_zakupki_soap_settings_cache()
