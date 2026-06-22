from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from src.modules.tender_operator_agent_demo.procurement_discovery import get_demo_procurement, search_procurements
from src.modules.tender_operator_agent_demo.procurement_sources import get_procurement_source_descriptors
from src.modules.tender_operator_agent_demo.schemas import (
    ProcurementAttachmentManifestItem,
    ProcurementRunCreateRequest,
    ProcurementRunDetailsResponse,
    ProcurementRunResponse,
    ProcurementSearchResult,
    TenderOperatorUploadedRunStatus,
)
from src.modules.tender_operator_agent_demo.upload_service import (
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


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _find_descriptor(code: str):
    for item in get_procurement_source_descriptors():
        if item.code == code:
            return item
    return None


def create_run_from_procurement(request: ProcurementRunCreateRequest) -> ProcurementRunResponse:
    descriptor = _find_descriptor(request.source)
    if descriptor is None:
        raise HTTPException(status_code=400, detail=f"Unknown procurement source: {request.source}")
    if not descriptor.enabled:
        raise HTTPException(status_code=400, detail=descriptor.note or "Source is disabled in demo mode")

    procurement = get_demo_procurement(request.source, request.procurement_id)
    if procurement is None:
        raise HTTPException(status_code=404, detail="Procurement was not found")

    search_snapshot = search_procurements(query=request.query or "", source=request.source, max_results=10)
    selected = next((item for item in search_snapshot.results if item.procurement_id == request.procurement_id), None)
    if selected is None:
        selected = ProcurementSearchResult(
            procurement_id=procurement.procurement_id,
            source=procurement.source,
            title=procurement.title,
            procurement_number=procurement.procurement_number,
            customer_name=procurement.customer_name,
            category=procurement.category,
            publication_date=procurement.publication_date,
            deadline=procurement.deadline,
            initial_price=procurement.initial_price,
            currency=procurement.currency,
            region=procurement.region,
            source_url=procurement.source_url,
            attachments_status=procurement.attachments_status,
            attachments_count=len(procurement.attachments),
            available_attachments_count=len(procurement.attachments),
            summary=procurement.summary,
            attachment_names=[item.name for item in procurement.attachments],
            source_note=procurement.source_note,
        )

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
        "Поиск закупки завершён, результаты получены из безопасного demo-local источника.",
        {"results_found": len(search_snapshot.results), "source": request.source},
    )
    append_demo_run_event(
        run_id,
        "procurement_selected",
        "Оператор выбрал закупку из результатов поиска.",
        {"procurement_id": selected.procurement_id, "title": selected.title},
    )

    files: list[dict[str, Any]] = []
    manifest: list[ProcurementAttachmentManifestItem] = []

    if procurement.attachments:
        append_demo_run_event(
            run_id,
            "attachments_download_started",
            "Начато безопасное получение публично доступной документации.",
            {"attachments_expected": len(procurement.attachments)},
        )
        for index, attachment in enumerate(procurement.attachments, start=1):
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
    else:
        manifest.append(
            ProcurementAttachmentManifestItem(
                name="documentation",
                stored_name=None,
                extension="",
                status="manual_upload_required",
                note="Автоматическое получение документации недоступно. Загрузите документы вручную.",
            )
        )
        append_demo_run_event(
            run_id,
            "manual_upload_required",
            "Автоматическое получение документации недоступно. Нужна ручная загрузка документов.",
            {"attachments_status": procurement.attachments_status},
        )
        status = TenderOperatorUploadedRunStatus.DOCS_REQUIRED

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
        "attachments_status": procurement.attachments_status if status == TenderOperatorUploadedRunStatus.DOCS_REQUIRED else "downloaded",
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

    procurement_dir = get_demo_run_procurement_dir(run_id)
    (procurement_dir / "procurement_metadata.json").write_text(
        selected.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (procurement_dir / "attachments_manifest.json").write_text(
        "[" + ",\n".join(item.model_dump_json() for item in manifest) + "]",
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
        warnings=[],
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
        import json

        manifest = [ProcurementAttachmentManifestItem.model_validate(item) for item in json.loads(manifest_path.read_text(encoding="utf-8"))]

    return ProcurementRunDetailsResponse(
        run_id=run_id,
        procurement=ProcurementSearchResult.model_validate(procurement_payload),
        attachments_status=metadata.get("attachments_status", "unknown"),
        attachments=manifest,
        events=load_demo_run_events(run_id),
    )
