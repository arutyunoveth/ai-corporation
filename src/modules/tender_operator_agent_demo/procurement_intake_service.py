from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from src.modules.tender_operator_agent_demo.attachment_downloader import download_procurement_attachments
from src.modules.tender_operator_agent_demo.procurement_discovery import (
    get_demo_procurement,
    get_procurement_details,
    search_procurements,
)
from src.modules.tender_operator_agent_demo.procurement_sources import get_procurement_source_descriptors
from src.modules.tender_operator_agent_demo.procurement_schemas import DocsArchiveResult, ProcurementDetails
from src.modules.tender_operator_agent_demo.schemas import (
    EisDocsArchiveRunRequest,
    ProcurementAttachmentManifestItem,
    ProcurementRunCreateRequest,
    ProcurementRunDetailsResponse,
    ProcurementRunResponse,
    ProcurementSearchResult,
    TenderOperatorUploadedRunStatus,
)
from src.modules.tender_operator_agent_demo.upload_service import (
    ALLOWED_EXTENSIONS,
    MAX_ZIP_ENTRY_COUNT,
    MAX_ZIP_TOTAL_BYTES,
    append_demo_run_event,
    build_demo_file_descriptor,
    ensure_demo_run_structure,
    get_demo_run_input_dir,
    get_demo_run_procurement_dir,
    load_demo_run_events,
    load_demo_run_metadata,
    make_demo_run_id,
    sanitize_demo_filename,
    save_demo_run_metadata,
)
from src.modules.tender_operator_agent_demo.settings import get_zakupki_soap_settings
from src.modules.tender_operator_agent_demo.zakupki_soap_client import ZakupkiSoapClient


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _find_descriptor(code: str):
    for item in get_procurement_source_descriptors():
        if item.code == code:
            return item
    return None


def _legacy_result_from_details(details: ProcurementDetails) -> ProcurementSearchResult:
    procurement = details.procurement
    downloadable_count = sum(1 for item in details.attachments if item.can_download)
    source_note = "; ".join(details.warnings) if details.warnings else details.raw_source_summary
    return ProcurementSearchResult(
        procurement_id=procurement.procurement_id,
        source=procurement.source,
        title=procurement.title,
        procurement_number=procurement.notice_number or procurement.registry_number,
        customer_name=procurement.customer_name,
        category=procurement.law or "Закупка",
        publication_date=procurement.publication_date,
        deadline=procurement.deadline,
        initial_price=procurement.initial_price,
        currency=procurement.currency,
        region=None,
        source_url=procurement.source_url,
        attachments_status=procurement.attachments_status,
        attachments_count=max(procurement.attachments_count, len(details.attachments)),
        available_attachments_count=downloadable_count,
        summary=procurement.status or details.raw_source_summary,
        attachment_names=[item.name for item in details.attachments],
        source_note=source_note,
    )


def _write_procurement_artifacts(
    run_id: str,
    *,
    selected: ProcurementSearchResult,
    manifest: list[ProcurementAttachmentManifestItem],
) -> None:
    procurement_dir = get_demo_run_procurement_dir(run_id)
    (procurement_dir / "procurement_metadata.json").write_text(
        selected.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (procurement_dir / "attachments_manifest.json").write_text(
        json.dumps([item.model_dump(mode="json") for item in manifest], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (procurement_dir / "source_summary.txt").write_text(
        "\n".join(
            [
                f"Источник: {selected.source}",
                f"Номер закупки: {selected.procurement_number or 'не указан'}",
                f"Карточка: {selected.source_url}",
                f"Статус документации: {selected.attachments_status}",
                f"Примечание: {selected.source_note or '—'}",
            ]
        ),
        encoding="utf-8",
    )


def _build_getdocs_result(reestr_number: str, archive_result: DocsArchiveResult) -> ProcurementSearchResult:
    warnings = list(archive_result.warnings)
    if archive_result.status != "completed":
        warnings.append("Документация getDocsIP не была получена автоматически.")
    return ProcurementSearchResult(
        procurement_id=reestr_number,
        source="zakupki_gov_ru_getdocs_ip",
        title=f"Документация ЕИС по номеру {reestr_number}",
        procurement_number=reestr_number,
        customer_name="Не указан",
        category="44-ФЗ",
        publication_date=None,
        deadline=None,
        initial_price=None,
        currency="RUB",
        region=None,
        source_url=archive_result.archive_url or "https://zakupki.gov.ru/",
        attachments_status="downloadable" if archive_result.archive_url else "manual_upload_required",
        attachments_count=1 if archive_result.archive_url else 0,
        available_attachments_count=1 if archive_result.archive_url else 0,
        summary=archive_result.raw_summary or f"Статус getDocsIP: {archive_result.status}",
        attachment_names=["documentation-archive.zip"] if archive_result.archive_url else [],
        source_note="Read-only getDocsIP intake для токена физлица.",
    )


def _extract_safe_archive_into_run(run_id: str, archive_path: Path) -> tuple[list[dict[str, Any]], list[ProcurementAttachmentManifestItem], int]:
    files: list[dict[str, Any]] = []
    manifest: list[ProcurementAttachmentManifestItem] = []
    extracted_count = 0
    input_dir = get_demo_run_input_dir(run_id)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()]
            if len(members) > MAX_ZIP_ENTRY_COUNT:
                manifest.append(
                    ProcurementAttachmentManifestItem(
                        name=archive_path.name,
                        stored_name=archive_path.name,
                        extension=".zip",
                        status="skipped",
                        note=f"ZIP archive contains too many entries. Limit: {MAX_ZIP_ENTRY_COUNT}.",
                    )
                )
                return files, manifest, extracted_count
            total_unpacked = sum(item.file_size for item in members)
            if total_unpacked > MAX_ZIP_TOTAL_BYTES:
                manifest.append(
                    ProcurementAttachmentManifestItem(
                        name=archive_path.name,
                        stored_name=archive_path.name,
                        extension=".zip",
                        status="skipped",
                        note="ZIP archive exceeds the safe unpacked size limit.",
                    )
                )
                return files, manifest, extracted_count

            for item in members:
                entry_path = Path(item.filename)
                if entry_path.is_absolute() or ".." in entry_path.parts:
                    manifest.append(
                        ProcurementAttachmentManifestItem(
                            name=item.filename,
                            stored_name=None,
                            extension=entry_path.suffix.lower(),
                            status="skipped",
                            note="ZIP entry was rejected because it contains an unsafe path.",
                        )
                    )
                    continue
                entry_name = entry_path.name
                ext = entry_path.suffix.lower()
                if ext not in ALLOWED_EXTENSIONS or ext == ".zip":
                    manifest.append(
                        ProcurementAttachmentManifestItem(
                            name=entry_name,
                            stored_name=None,
                            extension=ext,
                            status="skipped",
                            note="Формат вложения не входит в allowlist.",
                        )
                    )
                    continue
                raw = archive.read(item)
                original_name, stored_name = sanitize_demo_filename(entry_name, extracted_count + 1)
                (input_dir / stored_name).write_bytes(raw)
                extracted_count += 1
                files.append(
                    build_demo_file_descriptor(
                        file_id=f"FILE-{extracted_count:02d}",
                        original_name=original_name,
                        stored_name=stored_name,
                        size_bytes=len(raw),
                        content_type="application/octet-stream",
                        source="eis_getdocs_archive",
                    )
                )
                manifest.append(
                    ProcurementAttachmentManifestItem(
                        name=original_name,
                        stored_name=stored_name,
                        extension=ext,
                        status="saved",
                        note="Файл извлечён из getDocsIP архива в безопасном локальном режиме.",
                    )
                )
    except zipfile.BadZipFile:
        manifest.append(
            ProcurementAttachmentManifestItem(
                name=archive_path.name,
                stored_name=archive_path.name,
                extension=".zip",
                status="skipped",
                note="ZIP archive could not be read safely.",
            )
        )
    return files, manifest, extracted_count


def create_run_from_procurement(request: ProcurementRunCreateRequest) -> ProcurementRunResponse:
    descriptor = _find_descriptor(request.source)
    if descriptor is None:
        raise HTTPException(status_code=400, detail=f"Unknown procurement source: {request.source}")
    if not descriptor.enabled:
        raise HTTPException(status_code=400, detail=descriptor.note or "Source is disabled in demo mode")

    demo_procurement = get_demo_procurement(request.source, request.procurement_id)
    details: ProcurementDetails | None = None
    if demo_procurement is None:
        try:
            details = get_procurement_details(request.source, request.procurement_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        selected = _legacy_result_from_details(details)
        search_results_count = 1
    else:
        search_snapshot = search_procurements(query=request.query or "", source=request.source, max_results=10)
        selected = next((item for item in search_snapshot.results if item.procurement_id == request.procurement_id), None)
        if selected is None:
            selected = ProcurementSearchResult(
                procurement_id=demo_procurement.procurement_id,
                source=demo_procurement.source,
                title=demo_procurement.title,
                procurement_number=demo_procurement.procurement_number,
                customer_name=demo_procurement.customer_name,
                category=demo_procurement.category,
                publication_date=demo_procurement.publication_date,
                deadline=demo_procurement.deadline,
                initial_price=demo_procurement.initial_price,
                currency=demo_procurement.currency,
                region=demo_procurement.region,
                source_url=demo_procurement.source_url,
                attachments_status=demo_procurement.attachments_status,
                attachments_count=len(demo_procurement.attachments),
                available_attachments_count=len(demo_procurement.attachments),
                summary=demo_procurement.summary,
                attachment_names=[item.name for item in demo_procurement.attachments],
                source_note=demo_procurement.source_note,
            )
        search_results_count = len(search_snapshot.results)

    run_id = make_demo_run_id()
    ensure_demo_run_structure(run_id, exist_ok=False)
    created_at = _now_iso()

    append_demo_run_event(
        run_id,
        "procurement_search_started",
        "Запущен поиск закупки в безопасном read-only режиме.",
        {"query": request.query or "", "source": request.source},
    )
    append_demo_run_event(
        run_id,
        "procurement_search_completed",
        "Поиск закупки завершён, результаты получены из безопасного read-only источника.",
        {"results_found": search_results_count, "source": request.source},
    )
    append_demo_run_event(
        run_id,
        "procurement_selected",
        "Оператор выбрал закупку из результатов поиска.",
        {"procurement_id": selected.procurement_id, "title": selected.title},
    )
    append_demo_run_event(
        run_id,
        "procurement_details_loaded",
        "Детали выбранной закупки загружены в локальный demo-run.",
        {
            "procurement_id": selected.procurement_id,
            "notice_number": selected.procurement_number,
            "source_url": selected.source_url,
        },
    )
    attachments_expected = len(demo_procurement.attachments) if demo_procurement else len(details.attachments if details else [])
    append_demo_run_event(
        run_id,
        "attachments_list_loaded",
        "Список документации закупки получен для безопасного intake.",
        {"attachments_expected": attachments_expected, "attachments_status": selected.attachments_status},
    )

    files: list[dict[str, Any]] = []
    manifest: list[ProcurementAttachmentManifestItem] = []

    if demo_procurement and demo_procurement.attachments and request.download_attachments:
        append_demo_run_event(
            run_id,
            "attachments_download_started",
            "Начато безопасное получение публично доступной документации.",
            {"attachments_expected": len(demo_procurement.attachments)},
        )
        for index, attachment in enumerate(demo_procurement.attachments, start=1):
            original_name, stored_name = sanitize_demo_filename(attachment.name, index)
            target = get_demo_run_input_dir(run_id) / stored_name
            target.write_bytes(attachment.payload)
            files.append(
                build_demo_file_descriptor(
                    file_id=f"FILE-{index:02d}",
                    original_name=original_name,
                    stored_name=stored_name,
                    size_bytes=len(attachment.payload),
                    content_type=attachment.content_type,
                    source="procurement_download",
                )
            )
            manifest.append(
                ProcurementAttachmentManifestItem(
                    name=original_name,
                    stored_name=stored_name,
                    extension=Path(stored_name).suffix.lower(),
                    status="saved",
                    note="Файл сохранён в локальную demo-run директорию.",
                )
            )
            append_demo_run_event(
                run_id,
                "attachment_saved",
                f"Документация '{original_name}' сохранена локально.",
                {"stored_name": stored_name},
            )
        append_demo_run_event(
            run_id,
            "attachments_download_completed",
            "Документация сохранена локально и готова к анализу.",
            {"saved_files": len(files)},
        )
        status = TenderOperatorUploadedRunStatus.READY_TO_ANALYZE
    elif details and details.attachments and request.download_attachments:
        append_demo_run_event(
            run_id,
            "attachments_download_started",
            "Начато безопасное получение публично доступной документации.",
            {"attachments_expected": len(details.attachments), "source": request.source},
        )
        settings = get_zakupki_soap_settings()
        download_limit = settings.max_download_mb * 1024 * 1024
        download_result = download_procurement_attachments(
            details.attachments,
            target_dir=get_demo_run_input_dir(run_id),
            max_attachments=settings.max_attachments,
            max_file_size_bytes=download_limit,
            max_total_size_bytes=download_limit,
        )
        for index, item in enumerate(download_result.saved, start=1):
            if not item.stored_name:
                continue
            files.append(
                build_demo_file_descriptor(
                    file_id=f"FILE-{index:02d}",
                    original_name=item.name,
                    stored_name=item.stored_name,
                    size_bytes=item.size_bytes,
                    content_type="application/octet-stream",
                    source="procurement_download",
                )
            )
        for item in download_result.manifest:
            manifest_item = ProcurementAttachmentManifestItem(
                name=item.name,
                stored_name=item.stored_name,
                extension=item.extension,
                status=item.status,
                note=item.note,
            )
            manifest.append(manifest_item)
            append_demo_run_event(
                run_id,
                "attachment_saved" if item.status == "saved" else "attachment_skipped",
                (
                    f"Документация '{item.name}' сохранена локально."
                    if item.status == "saved"
                    else f"Документация '{item.name}' пропущена: {item.note or 'причина не указана'}"
                ),
                {"stored_name": item.stored_name, "status": item.status},
            )
        append_demo_run_event(
            run_id,
            "attachments_download_completed",
            "Получение документации завершено.",
            {"saved_files": len(files), "skipped_files": len(download_result.skipped)},
        )
        status = TenderOperatorUploadedRunStatus.READY_TO_ANALYZE if files else TenderOperatorUploadedRunStatus.DOCS_REQUIRED
    else:
        reason = (
            "Оператор создал run без автоматического скачивания документации."
            if not request.download_attachments
            else "Автоматическое получение документации недоступно. Загрузите документы вручную."
        )
        manifest.append(
            ProcurementAttachmentManifestItem(
                name="documentation",
                stored_name=None,
                extension="",
                status="manual_upload_required",
                note=reason,
            )
        )
        append_demo_run_event(
            run_id,
            "manual_upload_required",
            "Автоматическое получение документации недоступно. Нужна ручная загрузка документов.",
            {"attachments_status": selected.attachments_status, "download_attachments": request.download_attachments},
        )
        status = TenderOperatorUploadedRunStatus.DOCS_REQUIRED

    manual_upload_required = status == TenderOperatorUploadedRunStatus.DOCS_REQUIRED
    attachments_status = "downloaded" if files else "manual_upload_required"

    metadata = {
        "run_id": run_id,
        "created_at": created_at,
        "mode": "procurement_search_intake",
        "tender_title": selected.title,
        "tender_category": selected.category,
        "customer_name": selected.customer_name,
        "notes": request.query or None,
        "status": status.value,
        "analysis_mode": "not_started",
        "procurement_source": selected.source,
        "procurement_id": selected.procurement_id,
        "procurement_url": selected.source_url,
        "procurement_query": request.query or "",
        "publication_date": selected.publication_date,
        "deadline": selected.deadline,
        "attachments_status": attachments_status,
        "downloaded_files_count": len(files),
        "manual_upload_required": manual_upload_required,
        "source": selected.source,
        "notice_number": selected.procurement_number,
        "law": selected.category if selected.category in {"44-ФЗ", "223-ФЗ"} else None,
        "files": files,
        "warnings": [],
        "limitations": [
            "Поиск работает только в безопасном read-only режиме.",
            "Без авторизации, без обхода captcha, без внешних действий на площадках.",
            "Подача заявки, письма поставщикам и ЭЦП остаются вне этого demo-контура.",
        ],
        "human_in_the_loop": True,
        "external_actions": False,
        "no_platform_submission": True,
        "no_email_sending": True,
        "no_digital_signature": True,
        "procurement": selected.model_dump(mode="json"),
    }
    save_demo_run_metadata(run_id, metadata)

    _write_procurement_artifacts(run_id, selected=selected, manifest=manifest)
    append_demo_run_event(
        run_id,
        "run_created_from_procurement",
        "Создан run из выбранной закупки.",
        {"mode": "procurement_search_intake", "file_count": len(files)},
    )

    return ProcurementRunResponse(
        run_id=run_id,
        status=status,
        created_at=datetime.fromisoformat(created_at),
        file_count=len(files),
        run_url=f"/demo/tender-agent?run_id={run_id}",
        report_url=f"/demo/tender-agent/runs/{run_id}/report",
        downloaded_files_count=len(files),
        manual_upload_required=manual_upload_required,
        warnings=[],
        limitations=metadata["limitations"],
        attachments_status=metadata["attachments_status"],
        procurement=selected,
        attachments=manifest,
    )


def create_run_from_eis_docs_archive(request: EisDocsArchiveRunRequest) -> ProcurementRunResponse:
    if request.law.lower() != "44fz":
        raise HTTPException(status_code=400, detail="getDocsIP intake currently supports only 44fz in this demo contour")

    settings = get_zakupki_soap_settings()
    if not settings.configured:
        raise HTTPException(status_code=400, detail="Источник ЕИС не настроен: добавьте ZAKUPKI_GOV_RU_SOAP_TOKEN в .env.local")

    client = ZakupkiSoapClient(settings)
    archive_result = client.get_docs_by_reestr_number(request.reestr_number, subsystem_type=request.subsystem_type)
    selected = _build_getdocs_result(request.reestr_number, archive_result)

    run_id = make_demo_run_id()
    ensure_demo_run_structure(run_id, exist_ok=False)
    created_at = _now_iso()

    append_demo_run_event(
        run_id,
        "attachments_download_started",
        "Запрошена документация по номеру закупки через ЕИС getDocsIP.",
        {"reestr_number": request.reestr_number, "subsystem_type": request.subsystem_type},
    )

    manifest: list[ProcurementAttachmentManifestItem] = []
    files: list[dict[str, Any]] = []
    archive_downloaded = False
    documents_extracted_count = 0

    if archive_result.archive_url and request.download_archive:
        downloaded = client.download_archive(archive_result.archive_url, get_demo_run_input_dir(run_id))
        archive_downloaded = True
        append_demo_run_event(
            run_id,
            "attachment_saved",
            "Архив документации ЕИС сохранён локально.",
            {"stored_name": downloaded.stored_name, "size_bytes": downloaded.size_bytes},
        )
        manifest.append(
            ProcurementAttachmentManifestItem(
                name=downloaded.file_name,
                stored_name=downloaded.stored_name,
                extension=".zip",
                status="saved",
                note="Архив документации скачан через getDocsIP в read-only режиме.",
            )
        )
        extracted_files, extracted_manifest, documents_extracted_count = _extract_safe_archive_into_run(
            run_id,
            get_demo_run_input_dir(run_id) / downloaded.stored_name,
        )
        files.extend(extracted_files)
        manifest.extend(extracted_manifest)
        append_demo_run_event(
            run_id,
            "attachments_download_completed",
            "Архив документации получен и безопасно обработан.",
            {"documents_extracted_count": documents_extracted_count, "archive_downloaded": True},
        )
        status = TenderOperatorUploadedRunStatus.READY_TO_ANALYZE if files else TenderOperatorUploadedRunStatus.DOCS_REQUIRED
    else:
        note = (
            "Архив документации не получен из ответа getDocsIP. Нужна ручная загрузка документов."
            if not archive_result.archive_url
            else "Архив не скачивался автоматически по параметрам запроса."
        )
        manifest.append(
            ProcurementAttachmentManifestItem(
                name="documentation-archive",
                stored_name=None,
                extension=".zip",
                status="manual_upload_required",
                note=note,
            )
        )
        append_demo_run_event(
            run_id,
            "manual_upload_required",
            "Архив документации не получен автоматически. Продолжение возможно после ручной загрузки документов.",
            {"getdocs_status": archive_result.status, "archive_url_present": bool(archive_result.archive_url)},
        )
        status = TenderOperatorUploadedRunStatus.DOCS_REQUIRED

    metadata = {
        "run_id": run_id,
        "created_at": created_at,
        "mode": "procurement_search_intake",
        "tender_title": selected.title,
        "tender_category": "44-ФЗ",
        "customer_name": "Не указан",
        "notes": None,
        "status": status.value,
        "analysis_mode": "not_started",
        "procurement_source": "zakupki_gov_ru_getdocs_ip",
        "procurement_id": request.reestr_number,
        "procurement_url": selected.source_url,
        "procurement_query": request.reestr_number,
        "publication_date": None,
        "deadline": None,
        "attachments_status": "downloaded" if files else "manual_upload_required",
        "downloaded_files_count": len(files),
        "manual_upload_required": status == TenderOperatorUploadedRunStatus.DOCS_REQUIRED,
        "source": "zakupki_gov_ru_getdocs_ip",
        "notice_number": request.reestr_number,
        "law": "44-ФЗ",
        "files": files,
        "warnings": list(archive_result.warnings),
        "limitations": [
            "getDocsIP используется только для read-only получения документации по номеру закупки.",
            "Поиск закупки и получение документации разделены: keyword search не идёт через getDocsIP.",
            "Без логина, без обхода captcha, без подачи заявки, без писем и без ЭЦП.",
        ],
        "human_in_the_loop": True,
        "external_actions": False,
        "no_platform_submission": True,
        "no_email_sending": True,
        "no_digital_signature": True,
        "procurement": selected.model_dump(mode="json"),
        "token_owner": settings.token_owner,
        "reestr_number": request.reestr_number,
        "subsystem_type": request.subsystem_type,
        "archive_url_present": bool(archive_result.archive_url),
        "archive_downloaded": archive_downloaded,
        "documents_extracted_count": documents_extracted_count,
        "getdocs_status": archive_result.status,
        "getdocs_request_id": archive_result.request_id,
        "getdocs_ref_id": archive_result.ref_id,
        "archive_safe_diagnostic": archive_result.safe_diagnostic,
    }
    save_demo_run_metadata(run_id, metadata)
    _write_procurement_artifacts(run_id, selected=selected, manifest=manifest)
    append_demo_run_event(
        run_id,
        "run_created_from_procurement",
        "Создан run из архива документации ЕИС getDocsIP.",
        {"mode": "procurement_search_intake", "file_count": len(files), "token_owner": settings.token_owner},
    )
    return ProcurementRunResponse(
        run_id=run_id,
        status=status,
        created_at=datetime.fromisoformat(created_at),
        file_count=len(files),
        run_url=f"/demo/tender-agent/runs/{run_id}",
        report_url=f"/demo/tender-agent/runs/{run_id}/report",
        downloaded_files_count=len(files),
        manual_upload_required=status == TenderOperatorUploadedRunStatus.DOCS_REQUIRED,
        warnings=list(archive_result.warnings),
        limitations=metadata["limitations"],
        attachments_status=metadata["attachments_status"],
        procurement=selected,
        attachments=manifest,
    )


def get_procurement_for_run(run_id: str) -> ProcurementRunDetailsResponse:
    metadata = load_demo_run_metadata(run_id)
    procurement_payload = metadata.get("procurement")
    if not procurement_payload:
        raise HTTPException(status_code=404, detail="Procurement metadata is not available for this run")

    manifest_path = get_demo_run_procurement_dir(run_id) / "attachments_manifest.json"
    manifest = []
    if manifest_path.is_file():
        manifest = [ProcurementAttachmentManifestItem.model_validate(item) for item in json.loads(manifest_path.read_text(encoding="utf-8"))]

    return ProcurementRunDetailsResponse(
        run_id=run_id,
        procurement=ProcurementSearchResult.model_validate(procurement_payload),
        attachments_status=metadata.get("attachments_status", "unknown"),
        attachments=manifest,
        events=load_demo_run_events(run_id),
    )
