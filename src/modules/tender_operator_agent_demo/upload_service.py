from __future__ import annotations

import html
import json
import os
import re
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from secrets import token_hex
from typing import Any

from fastapi import HTTPException
from fastapi.responses import FileResponse

from src.modules.tender_connectors.text_extraction import extract_text_from_attachment_bytes
from src.modules.tender_operator_agent_demo.event_log import (
    append_tender_demo_event,
    load_tender_demo_events,
)
from src.modules.tender_operator_agent_demo.procurement_discovery import get_supplier_profile
from src.modules.tender_operator_agent_demo.relevance_scoring import score_procurement_document_text
from src.modules.supplier_search.internet_supplier_search import search_suppliers
from src.modules.supplier_search.yandex_search_client import YandexSearchClient
from src.shared.config.settings import get_settings
from src.modules.tender_operator_agent_demo.quote_normalizer import (
    SpreadsheetSource,
    build_economics_summary,
    build_quote_comparison,
)
from src.modules.tender_operator_agent_demo.schemas import (
    DemoDetailSection,
    DemoFinalRecommendation,
    DemoRecommendationCode,
    DemoStep,
    DemoStepStatus,
    TenderOperatorDemoReportResponse,
    TenderOperatorUploadedFile,
    TenderOperatorUploadedRunAnalyzeResponse,
    TenderOperatorUploadedRunCreateResponse,
    TenderOperatorUploadedRunListResponse,
    TenderOperatorUploadedRunResponse,
    TenderOperatorRunEvent,
    TenderOperatorUploadedRunStatus,
    TenderOperatorUploadedRunStepsResponse,
    TenderOperatorUploadedRunSummary,
)


ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".xlsx", ".xls", ".txt", ".csv", ".zip", ".xml"}
MAX_FILE_COUNT = 16
MAX_FILE_SIZE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_UPLOAD_BYTES = 40 * 1024 * 1024
MAX_ZIP_ENTRY_COUNT = 32
MAX_ZIP_TOTAL_BYTES = 24 * 1024 * 1024
METADATA_FILE = "metadata.json"
EVENTS_FILE = "events.jsonl"
DEFAULT_TARGET_MARGIN_PERCENT = 15.0
DEFAULT_LOGISTICS_RESERVE_PERCENT = 3.0
DEFAULT_RISK_RESERVE_PERCENT = 5.0
DEFAULT_PAYMENT_DELAY_DAYS = 45

TEXT_TRANSLATIONS = {
    "Compliance with specified technical standards required": "Требуется соответствие указанным техническим стандартам.",
    "Equipment/goods must match stated specifications": "Оборудование и товары должны соответствовать заявленной спецификации.",
    "Acceptance testing per contract terms": "Нужно пройти приёмочные испытания по условиям договора.",
    "Warranty and post-delivery support required": "Требуются гарантия и поддержка после поставки.",
    "Company registration certificate": "Свидетельство о регистрации компании.",
    "Tax clearance certificate": "Справка об отсутствии налоговой задолженности.",
    "Technical proposal with specifications": "Техническое предложение со спецификацией.",
    "Financial guarantee or contract security": "Финансовое обеспечение или обеспечение исполнения договора.",
    "Declaration of conformity": "Декларация о соответствии.",
    "Can you supply the exact item matching the specification? If not, what analog do you propose?": "Можете ли вы поставить точную позицию по спецификации? Если нет, какой аналог предлагаете?",
    "What is your price per unit with VAT and without VAT?": "Укажите цену за единицу с НДС и без НДС.",
    "What is the delivery cost to the specified location?": "Укажите стоимость доставки до указанного объекта.",
    "What is the delivery time from order confirmation?": "Какой срок поставки после подтверждения заказа?",
    "Is the item in stock or made to order? If made to order, what is the manufacturing lead time?": "Позиция в наличии или производится под заказ? Если под заказ, какой срок изготовления?",
    "Do you have the required certificates and declarations of conformity?": "Есть ли необходимые сертификаты и декларации соответствия?",
    "What warranty do you provide?": "Какой гарантийный срок вы предоставляете?",
    "Do you offer an analog that meets the specification? If so, provide details.": "Предлагаете ли аналог, соответствующий спецификации? Если да, укажите детали.",
    "What are your payment terms? Do you require prepayment?": "Какие условия оплаты? Требуется ли предоплата?",
    "How long is your offer valid?": "Какой срок действия вашего предложения?",
    "Is installation/assembly included? If not, what are the additional costs?": "Входит ли монтаж или сборка? Если нет, какие дополнительные затраты?",
    "Is packaging, delivery, and unloading included? If not, what are the additional costs?": "Включены ли упаковка, доставка и разгрузка? Если нет, какие дополнительные затраты?",
    "Penalties for delay": "Штрафы за просрочку.",
    "Post-payment after acceptance": "Оплата после приёмки.",
    "Unilateral termination right": "Право одностороннего расторжения.",
    "Contract security requirement": "Требование обеспечения исполнения договора.",
    "Short delivery timeline": "Сжатый срок поставки.",
    "Required license/SRO/experience": "Обязательная лицензия, СРО или подтверждённый опыт.",
    "Manageable. Include in project planning.": "Риск управляемый. Нужно заложить его в план исполнения.",
    "Standard for public procurement. Requires working capital.": "Типично для закупок. Требует оборотного капитала.",
    "Standard clause. Manageable with proper project management.": "Стандартное условие. Управляется при дисциплине исполнения.",
    "Binds significant working capital. Reduces available margin.": "Замораживает заметный объём оборотных средств и снижает доступную маржу.",
    "Requires supplier with stock or short manufacturing lead time.": "Нужен поставщик со складским остатком или коротким циклом производства.",
    "If operator/supplier cannot meet these, participation is impossible.": "Если оператор или поставщик не соответствуют этому требованию, участвовать нельзя.",
    "Ensure realistic delivery timeline. Include buffer.": "Подтвердить реалистичный срок поставки и заложить буфер.",
    "Factor into cash flow planning. Consider contract security reduction.": "Учесть это в cash-flow и отдельно оценить возможность снижения обеспечения.",
    "Track milestones diligently. Communicate proactively.": "Жёстко контролировать вехи исполнения и заранее эскалировать отклонения.",
    "Include cost of security (bank guarantee fee) in pricing. Negotiate reduction if possible.": "Включить стоимость обеспечения в цену и, если возможно, согласовать снижение.",
    "Verify supplier availability before bidding. Consider partial delivery.": "До участия подтвердить наличие у поставщика и рассмотреть частичную поставку.",
    "Verify requirements early. Check if equivalents are accepted.": "Сразу проверить требования и отдельно уточнить, принимаются ли эквиваленты.",
}


def _translate_user_text(value: str) -> str:
    return TEXT_TRANSLATIONS.get(value, value)


@dataclass
class AnalyzedDocument:
    display_name: str
    extension: str
    role: str
    text: str | None
    extracted_text_available: bool
    warnings: list[str]
    source: str
    file_id: str
    raw_content: bytes | None = None


def get_demo_runs_root() -> Path:
    configured = os.environ.get("AI_CORP_TENDER_OPERATOR_DEMO_RUNS_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[3] / "company_agent_runs" / "tender_operator_demo"


def _ensure_runs_root() -> Path:
    root = get_demo_runs_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_demo_run_dir(run_id: str) -> Path:
    return _ensure_runs_root() / run_id


def get_demo_run_procurement_dir(run_id: str) -> Path:
    return get_demo_run_dir(run_id) / "procurement"


def get_demo_run_input_dir(run_id: str) -> Path:
    return get_demo_run_dir(run_id) / "input"


def get_demo_run_normalized_dir(run_id: str) -> Path:
    return get_demo_run_dir(run_id) / "normalized"


def get_demo_run_output_dir(run_id: str) -> Path:
    return get_demo_run_dir(run_id) / "output"


def _events_path(run_id: str) -> Path:
    return get_demo_run_dir(run_id) / EVENTS_FILE


def _metadata_path(run_id: str) -> Path:
    return get_demo_run_dir(run_id) / METADATA_FILE


def _input_dir(run_id: str) -> Path:
    return get_demo_run_input_dir(run_id)


def _normalized_dir(run_id: str) -> Path:
    return get_demo_run_normalized_dir(run_id)


def _output_dir(run_id: str) -> Path:
    return get_demo_run_output_dir(run_id)


def _safe_datetime() -> str:
    return datetime.now(UTC).isoformat()


def make_demo_run_id() -> str:
    return f"toa-run-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{token_hex(3)}"


def sanitize_demo_filename(name: str, index: int) -> tuple[str, str]:
    original = Path(name or f"file-{index}").name
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext or 'unknown'}")

    stem = Path(original).stem.lower()
    stem = re.sub(r"[^a-z0-9._-]+", "-", stem).strip("._-")
    if not stem:
        stem = f"file-{index}"
    stem = stem[:60]
    stored_name = f"{index:02d}-{stem}{ext}"
    return original, stored_name


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_file_descriptor(
    *,
    file_id: str,
    original_name: str,
    stored_name: str,
    role_hint: str | None,
    size_bytes: int,
    content_type: str,
    ) -> dict[str, Any]:
    return {
        "file_id": file_id,
        "original_name": original_name,
        "display_name": original_name,
        "stored_name": stored_name,
        "role_hint": role_hint,
        "extension": Path(stored_name).suffix.lower(),
        "size_bytes": size_bytes,
        "content_type": content_type or "application/octet-stream",
        "source": "upload",
        "extracted_text_available": False,
        "warnings": [],
    }


def build_demo_file_descriptor(
    *,
    file_id: str,
    original_name: str,
    stored_name: str,
    role_hint: str | None = None,
    size_bytes: int,
    content_type: str,
    source: str = "upload",
) -> dict[str, Any]:
    descriptor = _build_file_descriptor(
        file_id=file_id,
        original_name=original_name,
        stored_name=stored_name,
        role_hint=role_hint,
        size_bytes=size_bytes,
        content_type=content_type,
    )
    descriptor["source"] = source
    return descriptor


def ensure_demo_run_structure(run_id: str, *, exist_ok: bool) -> dict[str, Path]:
    run_dir = get_demo_run_dir(run_id)
    input_dir = get_demo_run_input_dir(run_id)
    normalized_dir = get_demo_run_normalized_dir(run_id)
    output_dir = get_demo_run_output_dir(run_id)
    procurement_dir = get_demo_run_procurement_dir(run_id)
    input_dir.mkdir(parents=True, exist_ok=exist_ok)
    normalized_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    procurement_dir.mkdir(parents=True, exist_ok=True)
    return {
        "run_dir": run_dir,
        "input_dir": input_dir,
        "normalized_dir": normalized_dir,
        "output_dir": output_dir,
        "procurement_dir": procurement_dir,
    }


def load_demo_run_metadata(run_id: str) -> dict[str, Any]:
    path = _metadata_path(run_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' was not found")
    return _read_json(path)


def save_demo_run_metadata(run_id: str, metadata: dict[str, Any]) -> None:
    _write_json(_metadata_path(run_id), metadata)


def append_demo_run_event(run_id: str, event_type: str, message: str, details: dict[str, Any] | None = None) -> None:
    append_tender_demo_event(run_id, event_type, message, details or {})


def load_demo_run_events(run_id: str) -> list[TenderOperatorRunEvent]:
    return [TenderOperatorRunEvent.model_validate(item) for item in load_tender_demo_events(run_id)]


def _sanitize_percent(value: float | None, *, default: float, field_name: str) -> float:
    numeric = default if value is None else float(value)
    if numeric < 0 or numeric > 95:
        raise HTTPException(status_code=400, detail=f"{field_name} must be between 0 and 95")
    return round(numeric, 2)


def _sanitize_delay_days(value: int | None, *, default: int) -> int:
    numeric = default if value is None else int(value)
    if numeric < 0 or numeric > 365:
        raise HTTPException(status_code=400, detail="payment_delay_days must be between 0 and 365")
    return numeric


def create_uploaded_demo_run(
    *,
    tender_title: str,
    tender_category: str,
    customer_name: str,
    notes: str | None,
    target_margin_percent: float | None,
    logistics_reserve_percent: float | None,
    risk_reserve_percent: float | None,
    payment_delay_days: int | None,
    uploads: list[tuple[str, str, bytes]],
) -> TenderOperatorUploadedRunCreateResponse:
    if not tender_title.strip():
        raise HTTPException(status_code=400, detail="tender_title is required")
    if not uploads:
        raise HTTPException(status_code=400, detail="At least one file must be uploaded")
    if len(uploads) > MAX_FILE_COUNT:
        raise HTTPException(status_code=400, detail=f"Too many files. Limit: {MAX_FILE_COUNT}")

    total_size = sum(len(content) for _name, _ctype, content in uploads)
    if total_size > MAX_TOTAL_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Total upload size exceeds the allowed limit")

    target_margin_percent = _sanitize_percent(
        target_margin_percent,
        default=DEFAULT_TARGET_MARGIN_PERCENT,
        field_name="target_margin_percent",
    )
    logistics_reserve_percent = _sanitize_percent(
        logistics_reserve_percent,
        default=DEFAULT_LOGISTICS_RESERVE_PERCENT,
        field_name="logistics_reserve_percent",
    )
    risk_reserve_percent = _sanitize_percent(
        risk_reserve_percent,
        default=DEFAULT_RISK_RESERVE_PERCENT,
        field_name="risk_reserve_percent",
    )
    payment_delay_days = _sanitize_delay_days(payment_delay_days, default=DEFAULT_PAYMENT_DELAY_DAYS)

    run_id = make_demo_run_id()
    structure = ensure_demo_run_structure(run_id, exist_ok=False)
    input_dir = structure["input_dir"]

    warnings: list[str] = []
    files: list[dict[str, Any]] = []

    for index, (filename, content_type, content) in enumerate(uploads, start=1):
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=400, detail=f"File exceeds the allowed size limit: {filename}")

        original_name, stored_name = sanitize_demo_filename(filename, index)
        file_id = f"FILE-{index:02d}"
        target = input_dir / stored_name
        target.write_bytes(content)
        if Path(filename).name != filename or ".." in filename.replace("\\", "/"):
            warnings.append(f"Filename '{filename}' was normalized for safe local storage.")
        files.append(
            build_demo_file_descriptor(
                file_id=file_id,
                original_name=original_name,
                stored_name=stored_name,
                role_hint=_derive_role_hint(stored_name),
                size_bytes=len(content),
                content_type=content_type,
            )
        )

    metadata = {
        "run_id": run_id,
        "created_at": _safe_datetime(),
        "mode": "uploaded_demo",
        "tender_title": tender_title.strip(),
        "tender_category": tender_category.strip() or "Электротехническое оборудование",
        "customer_name": customer_name.strip() or "Промышленный заказчик",
        "notes": notes.strip() if notes and notes.strip() else None,
        "status": TenderOperatorUploadedRunStatus.READY_TO_ANALYZE.value,
        "analysis_mode": "not_started",
        "economics_inputs": {
            "target_margin_percent": target_margin_percent,
            "logistics_reserve_percent": logistics_reserve_percent,
            "risk_reserve_percent": risk_reserve_percent,
            "payment_delay_days": payment_delay_days,
        },
        "files": files,
        "warnings": warnings,
        "limitations": [
            "Только демо- и пилотный режим.",
            "Без внешних действий, без отправки писем, без подачи на площадку, без ЭЦП.",
        ],
        "human_in_the_loop": True,
        "external_actions": False,
        "no_platform_submission": True,
        "no_email_sending": True,
        "no_digital_signature": True,
    }
    save_demo_run_metadata(run_id, metadata)
    append_demo_run_event(
        run_id,
        "run_created",
        "Создан демонстрационный прогон с ручной загрузкой документов.",
        {"mode": "uploaded_demo", "file_count": len(files)},
    )
    return TenderOperatorUploadedRunCreateResponse(
        run_id=run_id,
        status=TenderOperatorUploadedRunStatus.READY_TO_ANALYZE,
        created_at=datetime.fromisoformat(metadata["created_at"]),
        file_count=len(files),
        warnings=warnings,
        limitations=metadata["limitations"],
    )


def append_files_to_demo_run(
    *,
    run_id: str,
    uploads: list[tuple[str, str, bytes]],
) -> TenderOperatorUploadedRunCreateResponse:
    metadata = _load_metadata(run_id)
    if not uploads:
        raise HTTPException(status_code=400, detail="At least one file must be uploaded")

    existing_files = metadata.get("files", [])
    if len(existing_files) + len(uploads) > MAX_FILE_COUNT:
        raise HTTPException(status_code=400, detail=f"Too many files. Limit: {MAX_FILE_COUNT}")

    existing_total = sum(int(item.get("size_bytes", 0)) for item in existing_files)
    new_total = sum(len(content) for _filename, _ctype, content in uploads)
    if existing_total + new_total > MAX_TOTAL_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Total upload size exceeds the allowed limit")

    input_dir = _input_dir(run_id)
    warnings = list(metadata.get("warnings", []))
    start_index = len(existing_files) + 1
    added_files = 0

    for index, (filename, content_type, content) in enumerate(uploads, start=start_index):
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=400, detail=f"File exceeds the allowed size limit: {filename}")
        original_name, stored_name = sanitize_demo_filename(filename, index)
        file_id = f"FILE-{index:02d}"
        (input_dir / stored_name).write_bytes(content)
        if Path(filename).name != filename or ".." in filename.replace("\\", "/"):
            warnings.append(f"Filename '{filename}' was normalized for safe local storage.")
        existing_files.append(
            build_demo_file_descriptor(
                file_id=file_id,
                original_name=original_name,
                stored_name=stored_name,
                role_hint=_derive_role_hint(stored_name),
                size_bytes=len(content),
                content_type=content_type,
                source="manual_upload",
            )
        )
        append_demo_run_event(
            run_id,
            "attachment_saved",
            f"Документ '{original_name}' добавлен в прогон вручную.",
            {"stored_name": stored_name, "source": "manual_upload"},
        )
        added_files += 1

    metadata["files"] = existing_files
    metadata["warnings"] = sorted(set(warnings))
    if metadata.get("status") == TenderOperatorUploadedRunStatus.DOCS_REQUIRED.value:
        metadata["status"] = TenderOperatorUploadedRunStatus.READY_TO_ANALYZE.value
    if metadata.get("attachments_status") in {"manual_upload_required", "unavailable_in_demo", "source_requires_authorization"}:
        metadata["attachments_status"] = "manual_upload_received"
    metadata["downloaded_files_count"] = len(existing_files)
    metadata["manual_upload_required"] = False
    save_demo_run_metadata(run_id, metadata)
    append_demo_run_event(
        run_id,
        "manual_upload_received",
        "Оператор добавил документы в существующий run.",
        {"added_files": added_files},
    )
    return TenderOperatorUploadedRunCreateResponse(
        run_id=run_id,
        status=TenderOperatorUploadedRunStatus(metadata["status"]),
        created_at=datetime.fromisoformat(metadata["created_at"]),
        file_count=len(existing_files),
        warnings=metadata.get("warnings", []),
        limitations=metadata.get("limitations", []),
    )


def list_uploaded_demo_runs() -> TenderOperatorUploadedRunListResponse:
    root = _ensure_runs_root()
    runs: list[TenderOperatorUploadedRunSummary] = []
    for path in sorted(root.iterdir(), reverse=True):
        metadata_path = path / METADATA_FILE
        if not metadata_path.is_file():
            continue
        metadata = _read_json(metadata_path)
        runs.append(
            TenderOperatorUploadedRunSummary(
                run_id=metadata["run_id"],
                created_at=datetime.fromisoformat(metadata["created_at"]),
                mode=metadata["mode"],
                tender_title=metadata["tender_title"],
                tender_category=metadata["tender_category"],
                customer_name=metadata["customer_name"],
                status=TenderOperatorUploadedRunStatus(metadata["status"]),
                analysis_mode=metadata.get("analysis_mode", "not_started"),
                file_count=len(metadata.get("files", [])),
                warning_count=len(metadata.get("warnings", [])),
                limitations=metadata.get("limitations", []),
                procurement_source=metadata.get("procurement_source"),
                procurement_id=metadata.get("procurement_id"),
                attachments_status=metadata.get("attachments_status"),
            )
        )
    runs.sort(key=lambda item: item.created_at, reverse=True)
    return TenderOperatorUploadedRunListResponse(runs=runs[:12])


def _load_metadata(run_id: str) -> dict[str, Any]:
    return load_demo_run_metadata(run_id)


def _save_metadata(run_id: str, metadata: dict[str, Any]) -> None:
    save_demo_run_metadata(run_id, metadata)


def _decode_text(content: bytes) -> str | None:
    for encoding in ("utf-8", "cp1251", "koi8-r", "latin-1"):
        try:
            text = content.decode(encoding).strip()
            if text:
                return text
        except Exception:
            continue
    return None


def _detect_role(name: str) -> str:
    lowered = name.lower()
    if lowered.endswith(".xml") and any(
        token in lowered
        for token in (
            "epnotification",
            "epprotocol",
            "fcsplacementresult",
            "fcsproposalsresult",
            "clarification",
            "protocol",
        )
    ):
        return "notice"
    if any(token in lowered for token in ("tkp", "quote", "kp", "коммер", "proposal")):
        return "tkp"
    if any(token in lowered for token in ("contract", "договор", "agreement")):
        return "contract_draft"
    if any(token in lowered for token in ("spec", "специф", "technical", "тз", "техничес")):
        return "technical_spec"
    if any(token in lowered for token in ("notice", "извещ", "tender", "закуп")):
        return "notice"
    return "supporting"


def _derive_role_hint(filename: str) -> str | None:
    lowered = filename.lower()
    if lowered.startswith("technical_spec_"):
        return "technical_spec"
    if lowered.startswith("contract_draft_"):
        return "contract_draft"
    if lowered.startswith("notice_"):
        return "notice"
    if lowered.startswith("tkp_"):
        return "tkp"
    detected = _detect_role(filename)
    return detected if detected != "supporting" else None


def _extract_document_text(file_name: str, content: bytes) -> tuple[str | None, list[str]]:
    ext = Path(file_name).suffix.lower()
    warnings: list[str] = []
    if ext in {".txt", ".csv", ".xml"}:
        return _decode_text(content), warnings
    if ext in {".pdf", ".docx"}:
        text = extract_text_from_attachment_bytes(url=file_name, content=content)
        if text:
            return text, warnings
        warnings.append(f"Извлечение текста для {ext} в демо-режиме ограничено.")
        return None, warnings
    if ext == ".doc":
        text = _extract_text_from_legacy_doc(content)
        if text:
            return text, warnings
        warnings.append("Извлечение текста для .doc в демо-режиме ограничено.")
        return None, warnings
    if ext in {".xlsx", ".xls"}:
        warnings.append(f"Извлечение текста для {ext} в демо-режиме ограничено.")
        return None, warnings
    return None, warnings


def _extract_text_from_legacy_doc(content: bytes) -> str | None:
    try:
        with tempfile.TemporaryDirectory(prefix="toa-doc-") as tmp_dir:
            source_path = Path(tmp_dir) / "source.doc"
            output_path = Path(tmp_dir) / "source.txt"
            source_path.write_bytes(content)
            completed = subprocess.run(
                ["textutil", "-convert", "txt", "-output", str(output_path), str(source_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0 or not output_path.is_file():
                return None
            return _decode_text(output_path.read_bytes())
    except Exception:
        return None


def _extract_zip_documents(path: Path, parent_file_id: str) -> list[AnalyzedDocument]:
    documents: list[AnalyzedDocument] = []
    try:
        with zipfile.ZipFile(path) as archive:
            members = [info for info in archive.infolist() if not info.is_dir()]
            if len(members) > MAX_ZIP_ENTRY_COUNT:
                return [
                    AnalyzedDocument(
                        display_name=path.name,
                        extension=".zip",
                        role="supporting",
                        text=None,
                        extracted_text_available=False,
                        warnings=[f"ZIP archive contains too many entries. Limit: {MAX_ZIP_ENTRY_COUNT}."],
                        source="zip",
                        file_id=parent_file_id,
                        raw_content=None,
                    )
                ]
            total_unpacked = sum(info.file_size for info in members)
            if total_unpacked > MAX_ZIP_TOTAL_BYTES:
                return [
                    AnalyzedDocument(
                        display_name=path.name,
                        extension=".zip",
                        role="supporting",
                        text=None,
                        extracted_text_available=False,
                        warnings=["ZIP archive exceeds the safe unpacked size limit."],
                        source="zip",
                        file_id=parent_file_id,
                        raw_content=None,
                    )
                ]

            for idx, info in enumerate(members, start=1):
                entry_path = Path(info.filename)
                if entry_path.is_absolute() or ".." in entry_path.parts:
                    documents.append(
                        AnalyzedDocument(
                            display_name=f"{path.name} :: {info.filename}",
                            extension=entry_path.suffix.lower(),
                            role="supporting",
                            text=None,
                            extracted_text_available=False,
                            warnings=["ZIP entry was rejected because it contains an unsafe path."],
                            source="zip",
                            file_id=f"{parent_file_id}-ZIP-{idx:02d}",
                            raw_content=None,
                        )
                    )
                    continue
                entry_name = entry_path.name
                ext = Path(entry_name).suffix.lower()
                if ext not in ALLOWED_EXTENSIONS or ext == ".zip":
                    continue
                raw = archive.read(info)
                text, warnings = _extract_document_text(entry_name, raw)
                documents.append(
                    AnalyzedDocument(
                        display_name=f"{path.name} :: {entry_name}",
                        extension=ext,
                        role=_detect_role(entry_name),
                        text=text,
                        extracted_text_available=bool(text),
                        warnings=warnings,
                        source="zip",
                        file_id=f"{parent_file_id}-ZIP-{idx:02d}",
                        raw_content=raw,
                    )
                )
    except zipfile.BadZipFile:
        return [
            AnalyzedDocument(
                display_name=path.name,
                extension=".zip",
                role="supporting",
                text=None,
                extracted_text_available=False,
                warnings=["ZIP archive could not be read safely."],
                source="zip",
                file_id=parent_file_id,
                raw_content=None,
            )
        ]
    return documents


def _collect_documents(run_id: str, metadata: dict[str, Any]) -> list[AnalyzedDocument]:
    documents: list[AnalyzedDocument] = []
    normalized_dir = _normalized_dir(run_id)
    normalized_dir.mkdir(parents=True, exist_ok=True)

    for item in metadata.get("files", []):
        stored_path = _input_dir(run_id) / item["stored_name"]
        ext = Path(item["stored_name"]).suffix.lower()
        if ext == ".zip":
            extracted_docs = _extract_zip_documents(stored_path, item["file_id"])
            documents.extend(extracted_docs)
            if extracted_docs:
                item["warnings"] = list(dict.fromkeys(item.get("warnings", []) + ["ZIP archive inspected in safe local mode."]))
            continue

        raw = stored_path.read_bytes()
        text, warnings = _extract_document_text(item["stored_name"], raw)
        role = item.get("role_hint") or _detect_role(item["stored_name"])
        if text:
            normalized_name = f"{item['file_id'].lower()}-{role}.txt"
            (normalized_dir / normalized_name).write_text(text, encoding="utf-8")
        item["warnings"] = list(dict.fromkeys(item.get("warnings", []) + warnings))
        item["extracted_text_available"] = bool(text)
        documents.append(
            AnalyzedDocument(
                display_name=item["display_name"],
                extension=ext,
                role=role,
                text=text,
                extracted_text_available=bool(text),
                warnings=warnings,
                source="upload",
                file_id=item["file_id"],
                raw_content=raw,
            )
        )
    return documents


def _collect_role_text(documents: list[AnalyzedDocument], role: str) -> str:
    texts = [doc.text for doc in documents if doc.role == role and doc.text]
    return "\n\n".join(texts).strip()


def _collect_quote_paths(run_id: str, metadata: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    for item in metadata.get("files", []):
        if _detect_role(item["stored_name"]) == "tkp":
            paths.append(_input_dir(run_id) / item["stored_name"])
    return paths


def _collect_spreadsheet_sources(documents: list[AnalyzedDocument]) -> list[SpreadsheetSource]:
    return [
        SpreadsheetSource(
            file_id=doc.file_id,
            display_name=doc.display_name,
            source_file=doc.display_name,
            extension=doc.extension,
            raw_content=doc.raw_content or b"",
            source=doc.source,
            role_hint=doc.role,
        )
        for doc in documents
        if doc.extension in {".xlsx", ".xls"} and doc.raw_content
    ]


def _serialize_quote_comparison(quote_comparison) -> dict[str, Any]:
    return quote_comparison.model_dump(mode="json")


def _serialize_economics_summary(economics_summary) -> dict[str, Any]:
    return economics_summary.model_dump(mode="json")


def _maybe_float(value: Any) -> float | None:
    if value in (None, "", "unknown"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_quote_comparison_payload(payload: dict[str, Any]):
    from src.modules.tender_operator_agent_demo.schemas import QuoteComparison

    suppliers = []
    for index, item in enumerate(payload.get("suppliers", []), start=1):
        if isinstance(item, dict) and "supplier_id" in item and "supplier_name" in item:
            suppliers.append(item)
            continue
        suppliers.append(
            {
                "supplier_id": f"SUP-{index:02d}",
                "supplier_name": item.get("supplier_name") or item.get("supplier") or item.get("supplier_label") or f"Supplier {index}",
                "source_file": item.get("source_file") or item.get("supplier_label") or "uploaded quote",
                "source_sheet": item.get("source_sheet"),
                "document_type": item.get("document_type", "legacy_quote_placeholder"),
                "total_amount": _maybe_float(item.get("total_amount") or item.get("price_total")),
                "currency": item.get("currency", "RUB"),
                "items_count": item.get("items_count", 0),
                "delivery_summary": item.get("delivery_summary") or item.get("delivery_time_days"),
                "completeness_score": item.get("completeness_score", 0.0),
                "price_confidence": item.get("price_confidence", 0.0),
                "warnings": item.get("warnings", []),
                "items": item.get("items", []),
            }
        )
    manual_checks = [
        item if isinstance(item, dict) else {"code": "manual_check", "message": str(item)}
        for item in payload.get("manual_checks", [])
    ]
    warnings = [
        item if isinstance(item, dict) else {"code": "warning", "message": str(item)}
        for item in payload.get("warnings", [])
    ]
    return QuoteComparison.model_validate(
            {
                "status": payload.get("status", "blocked"),
                "analysis_mode": payload.get("analysis_mode", "unknown"),
                "supplier_quotes_found": payload.get("supplier_quotes_found", 0),
                "items_extracted": payload.get("items_extracted", 0),
                "suppliers": suppliers,
                "items": payload.get("items", []),
                "comparison_summary": payload.get("comparison_summary", {}),
                "manual_checks": manual_checks,
            "warnings": warnings,
            "limitations": payload.get("limitations", []),
        }
    )


def _coerce_economics_summary_payload(payload: dict[str, Any]):
    from src.modules.tender_operator_agent_demo.schemas import EconomicsSummary

    manual_checks = [
        item if isinstance(item, dict) else {"code": "manual_check", "message": str(item)}
        for item in payload.get("manual_checks", [])
    ]
    warnings = [
        item if isinstance(item, dict) else {"code": "warning", "message": str(item)}
        for item in payload.get("warnings", [])
    ]
    return EconomicsSummary.model_validate(
        {
            "status": payload.get("status", "blocked"),
            "analysis_mode": payload.get("analysis_mode", "unknown"),
            "currency": payload.get("currency"),
            "supplier_cost_min": payload.get("supplier_cost_min"),
            "supplier_cost_selected": payload.get("supplier_cost_selected"),
            "expected_revenue": payload.get("expected_revenue"),
            "preliminary_bid_price": payload.get("preliminary_bid_price"),
            "gross_margin_amount": payload.get("gross_margin_amount"),
            "gross_margin_percent": payload.get("gross_margin_percent"),
            "logistics_reserve": payload.get("logistics_reserve"),
            "risk_reserve": payload.get("risk_reserve"),
            "payment_delay_days": payload.get("payment_delay_days"),
            "cash_gap_estimate": payload.get("cash_gap_estimate"),
            "economics_status": payload.get("economics_status", "insufficient_data"),
            "selected_supplier_name": payload.get("selected_supplier_name"),
            "assumptions": payload.get("assumptions", {}),
            "manual_checks": manual_checks,
            "warnings": warnings,
            "limitations": payload.get("limitations", []),
        }
    )


def _import_runner_module():
    from scripts import run_tender_operator_pilot as pilot_runner

    return pilot_runner


def _try_run_llm_workflow(
    run_id: str,
    notice_text: str | None,
    technical_spec_text: str | None,
    contract_draft_text: str | None,
    quote_paths: list[Path],
    provider_mode: str = "llm",
) -> dict[str, Any] | None:
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from src.modules.controlled_llm_prebid.service import run_controlled_tender_operator_workflow
        from src.shared.db.base import Base

        settings = get_settings()
        if not settings.database_url:
            return None

        engine = create_engine(settings.database_url)
        Base.metadata.create_all(engine)

        context = {
            "deal_id": f"DEMO-{run_id}",
            "operator_id": "tender_operator_demo",
            "operator_profile": {},
            "documents": {
                "notice_text": notice_text or "",
                "technical_spec_text": technical_spec_text or "",
                "contract_draft_text": contract_draft_text or "",
            },
            "workflow_guardrails": {
                "manual_only": True,
                "no_email_send": True,
                "no_platform_submission": True,
                "human_review_required": True,
            },
            "tkp_inputs": [],
        }
        with Session(engine) as session:
            result = run_controlled_tender_operator_workflow(
                session,
                provider_mode=provider_mode,
                context=context,
                include_quote_normalization=False,
                include_bid_decision=False,
                simulate_invalid_output=False,
                provider_name_override=None,
            )
            return {
                "analysis_mode": result.analysis_mode,
                "resolved_provider": result.resolved_provider,
                "requirements": result.requirements,
                "supplier_questions": result.supplier_questions,
                "rfq_draft": result.rfq_draft,
                "contract_risks": result.contract_risks,
                "bid_decision": result.bid_decision,
            }
    except Exception:
        return None


def _run_supplier_internet_search(
    tender_title: str,
    notice_text: str | None = None,
    technical_spec_text: str | None = None,
) -> SupplierSearchOutcome:
    from src.modules.supplier_search.internet_supplier_search import SupplierSearchOutcome, search_suppliers
    from src.modules.supplier_search.yandex_search_client import YandexSearchClient

    settings = get_settings()
    api_key = settings.yandex_search_api_key
    folder_id = settings.yandex_search_folder_id
    if not api_key or not folder_id:
        return SupplierSearchOutcome(error="Yandex Search API не настроен. Добавьте AI_CORP_YANDEX_SEARCH_API_KEY и AI_CORP_YANDEX_SEARCH_FOLDER_ID.")
    try:
        client = YandexSearchClient(api_key=api_key, folder_id=folder_id, timeout=30)
        return search_suppliers(
            client=client,
            tender_title=tender_title,
            notice_text=notice_text,
            technical_spec_text=technical_spec_text,
            max_results=10,
        )
    except Exception:
        return SupplierSearchOutcome(error="Не удалось выполнить поиск поставщиков через Yandex Search API.")


def _infer_procurement_kind(*texts: str | None) -> str:
    combined = " ".join((text or "").lower() for text in texts if text)
    if not combined:
        return "generic"
    service_markers = (
        "оказание услуг",
        "образовательных услуг",
        "обучение",
        "слушател",
        "исполнитель",
        "программа повышения квалификации",
        "место оказания услуг",
    )
    goods_markers = (
        "поставка",
        "товар",
        "оборудован",
        "поставк",
        "склад",
        "разгруз",
        "гарантия на товар",
    )
    service_score = sum(combined.count(marker) for marker in service_markers)
    goods_score = sum(combined.count(marker) for marker in goods_markers)
    if service_score > goods_score:
        return "services"
    if goods_score > service_score:
        return "goods"
    return "generic"


def _normalize_requirement_title(title: str, procurement_kind: str) -> str | None:
    translated = _translate_user_text(title)
    if procurement_kind != "services":
        return translated
    service_specific = {
        "Требуется соответствие указанным техническим стандартам.": "Услуги должны соответствовать требованиям технического задания и обязательным нормативам.",
        "Оборудование и товары должны соответствовать заявленной спецификации.": "Услуги должны быть оказаны в полном объеме и в соответствии с техническим заданием.",
        "Нужно пройти приёмочные испытания по условиям договора.": "Приемка услуг проводится по условиям контракта.",
        "Требуются гарантия и поддержка после поставки.": "Исполнитель должен обеспечить качественное оказание услуг и выдать предусмотренные итоговые документы.",
        "Техническое предложение со спецификацией.": "Описание программы, графика и состава оказываемых услуг.",
        "Декларация о соответствии.": "Документы, подтверждающие соответствие обязательным требованиям закупки.",
    }
    return service_specific.get(translated, translated)


def _extract_requirement_rows(requirements: dict[str, Any], core_complete: bool, procurement_kind: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for title in requirements.get("technical_requirements", []):
        normalized_title = _normalize_requirement_title(title, procurement_kind)
        if not normalized_title:
            continue
        rows.append(
            {
                "title": normalized_title,
                "detail": "Извлечено детерминированным адаптером из доступных документов.",
                "source": "адаптер раннера" if core_complete else "fallback-адаптер",
            }
        )
    for title in requirements.get("document_requirements", []):
        normalized_title = _normalize_requirement_title(title, procurement_kind)
        if not normalized_title:
            continue
        rows.append(
            {
                "title": normalized_title,
                "detail": "Требование к комплекту документов или подтверждению квалификации.",
                "source": "адаптер раннера" if core_complete else "fallback-адаптер",
            }
        )
    return rows[:10]


def _match_first(text: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            value = " ".join(group for group in match.groups() if group)
            value = re.sub(r"\s+", " ", value).strip(" .;,\n\t")
            if value:
                return value
    return None


def _collect_matches(text: str, patterns: tuple[str, ...], *, limit: int = 6) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            value = " ".join(group for group in match.groups() if group)
            value = re.sub(r"\s+", " ", value).strip(" .;,\n\t")
            if not value:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            found.append(value)
            if len(found) >= limit:
                return found
    return found


def _match_first_dotall(text: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            value = " ".join(group for group in match.groups() if group)
            value = re.sub(r"\s+", " ", value).strip(" .;,\n\t")
            if value:
                return value
    return None


def _normalize_analysis_sentence(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip(" .;,\n\t")
    if not cleaned:
        return None
    cleaned = cleaned[0].upper() + cleaned[1:] if len(cleaned) > 1 else cleaned.upper()
    if cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def _dedupe_text_items(items: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = re.sub(r"\s+", " ", (item or "")).strip(" .").lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(item)
    return unique


def _shorten_payment_terms(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"(\d+)\s*\([^)]+\)\s*рабочих дней", r"\1 рабочих дней", value, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"после подписания Сторонами в единой информационной системе документа о приемке",
        "после подписания документа о приемке",
        cleaned,
        flags=re.IGNORECASE,
    )
    return _normalize_analysis_sentence(cleaned)


def _shorten_acceptance_terms(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"(\d+)\s*\([^)]+\)\s*рабочих дней", r"\1 рабочих дней", value, flags=re.IGNORECASE)
    cleaned = re.sub(
        r",?\s*следующих за днем поступления документа о приемке.*",
        " после поступления документа о приемке",
        cleaned,
        flags=re.IGNORECASE,
    )
    return _normalize_analysis_sentence(cleaned)


def _format_money_value(value: float | str | None) -> str | None:
    if value in (None, ""):
        return None
    try:
        numeric = float(str(value).replace(" ", "").replace(",", "."))
    except ValueError:
        return str(value)
    return f"{numeric:,.2f}".replace(",", " ").replace(".", ",")


def _rewrite_compliance_highlight(value: str) -> str:
    lowered = value.lower()
    if "федеральной служ" in lowered and "техническому и экспортному контролю" in lowered:
        return "Программа должна быть согласована с ФСТЭК России."
    if "удостоверени" in lowered and "повышени" in lowered:
        return "По итогам обучения нужно выдать удостоверение о повышении квалификации."
    if "аттестаци" in lowered:
        return "Нужно провести итоговую аттестацию слушателей."
    if "учебный план должен содержать" in lowered:
        return "Учебный план должен содержать перечень тем и распределение часов."
    if "раздаточ" in lowered and "материал" in lowered:
        return "Исполнитель должен обеспечить слушателей учебными и раздаточными материалами."
    return _normalize_analysis_sentence(value) or value


def _rewrite_delivery_model_item(value: str, procurement_kind: str) -> str:
    lowered = value.lower()
    if procurement_kind == "services":
        if "очно-заочная" in lowered:
            return "Формат обучения: очно-заочный, с применением дистанционных образовательных технологий."
        if "дистанцион" in lowered:
            return "Часть программы проводится дистанционно на стороне заказчика."
        if "60" in lowered and "%" in lowered:
            return "Около 60% программы проходит в очном формате."
        if "40" in lowered and "%" in lowered:
            return "Около 40% программы проходит дистанционно."
        if "09.00" in value or "18.00" in value:
            return "Режим занятий: с 09:00 до 18:00."
        if "городе хабаровске" in lowered:
            return "Очная часть должна проходить в городе Хабаровске."
    return _normalize_analysis_sentence(value) or value


def _cleanup_tabular_value(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip(" .;,\n\t")
    cleaned = re.sub(r"\s+([,.:;])", r"\1", cleaned)
    cleaned = re.sub(r"([A-Za-zА-Яа-яЁё])\s+(\d)", r"\1 \2", cleaned)
    cleaned = re.sub(r"(\d)\s+([A-Za-zА-Яа-яЁё])", r"\1 \2", cleaned)
    return cleaned or None


def _extract_inline_goods_field(text: str, labels: tuple[str, ...], *, stop_markers: tuple[str, ...]) -> str | None:
    if not text:
        return None
    label_pattern = "|".join(re.escape(label) for label in labels)
    stop_pattern = "|".join(re.escape(marker) for marker in stop_markers)
    match = re.search(
        rf"(?:{label_pattern})[^:\n]*[:\-]?\s*(.+?)(?=\s*(?:{stop_pattern})|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    return _cleanup_tabular_value(match.group(1))


def _extract_goods_characteristics(section_text: str) -> str | None:
    normalized = _cleanup_tabular_value(section_text) or ""
    matches = re.findall(
        r"([А-ЯA-ZЁ][А-ЯA-Zа-яa-zЁё0-9 ,()/%-]{1,60})\s*:\s*([^:]{1,80}?)(?=\s+\d+\s+[А-ЯA-ZЁ]|$)",
        normalized,
    )
    items: list[str] = []
    for name, value in matches:
        left = _cleanup_tabular_value(name)
        right = _cleanup_tabular_value(value)
        if not left or not right:
            continue
        if left.lower().startswith(("параметры для", "инструкция по", "обоснование", "описание объекта закупки")):
            continue
        items.append(f"{left}: {right}")
        if len(items) >= 4:
            break
    return "; ".join(items) if items else None


def _extract_goods_spec_table(technical_spec_text: str) -> list[dict[str, str]]:
    if not technical_spec_text:
        return []
    unit_pattern = r"(шт|м|компл(?:ект)?|упак(?:овка)?|пара|кг|л|рул(?:он)?|набор|ед\.?|усл\.?\s*ед\.?|услуга)"
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    section_pattern = re.compile(
        r"(?:(?P<section_no>\d(?:\s*\d)?)\.\s*)?Описание\s+объекта\s+закупки:",
        re.IGNORECASE,
    )
    matches = list(section_pattern.finditer(technical_spec_text))
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(technical_spec_text)
        section = technical_spec_text[start:end]
        section_number = re.sub(r"\s+", "", match.group("section_no") or "") or str(len(rows) + 1)
        row_match = re.search(
            r"1\s+2\s+3\s+4\s+5\s+6\s+7\s+(?P<row>.+?)(?=Характеристики\s+объекта\s+закупки:|$)",
            section,
            re.IGNORECASE | re.DOTALL,
        )
        if not row_match:
            continue
        row_text = _cleanup_tabular_value(row_match.group("row")) or ""
        if len(section_number) > 1:
            spaced_number = " ".join(section_number)
            if row_text.startswith(f"{spaced_number} "):
                row_text = f"{section_number} {row_text[len(spaced_number) + 1:]}"
        parsed_match = re.search(
            rf"(?P<num>\d+)\s+(?P<name>.+?)\s+(?P<unit>{unit_pattern})\s+(?P<tail>.+)$",
            row_text,
            re.IGNORECASE,
        )
        if parsed_match:
            number = section_number or parsed_match.group("num")
            name = _cleanup_tabular_value(parsed_match.group("name")) or "Позиция"
            unit = _cleanup_tabular_value(parsed_match.group("unit")) or "—"
            tail = _cleanup_tabular_value(parsed_match.group("tail")) or ""
            tail_tokens = tail.split()
            trailing_digit_tokens: list[str] = []
            for token in reversed(tail_tokens):
                stripped = token.strip()
                if stripped in {"-", "—"} and trailing_digit_tokens:
                    continue
                if re.fullmatch(r"\d+", stripped):
                    trailing_digit_tokens.append(stripped)
                    continue
                break
            quantity = "".join(reversed(trailing_digit_tokens)) if trailing_digit_tokens else "не указано"
        else:
            number = section_number
            name = row_text[:120] or "Позиция"
            unit = "—"
            quantity = "не указано"
        characteristics = _extract_goods_characteristics(section) or "Требуется сверка характеристик по ТЗ."
        dedupe_key = (name.lower(), unit.lower(), quantity, characteristics.lower())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        rows.append(
            {
                "№": number,
                "Наименование": name,
                "Ед. изм.": unit,
                "Кол-во": quantity or "не указано",
                "Характеристики": characteristics,
            }
        )
        if len(rows) >= 24:
            break
    final_rows: list[dict[str, str]] = []
    final_seen: set[tuple[str, str, str, str]] = set()
    for row in rows:
        key = (
            re.sub(r"\s+", " ", row.get("Наименование", "")).strip().lower(),
            re.sub(r"\s+", " ", row.get("Ед. изм.", "")).strip().lower(),
            re.sub(r"\s+", "", row.get("Кол-во", "")).strip().lower(),
            re.sub(r"\s+", " ", row.get("Характеристики", "")).strip().lower(),
        )
        if key in final_seen:
            continue
        final_seen.add(key)
        final_rows.append(row)
    return final_rows


def _build_goods_preliminary_analysis(
    *,
    metadata: dict[str, Any],
    technical_spec_text: str,
    contract_draft_text: str,
    notice_text: str,
) -> dict[str, Any]:
    tz_text = technical_spec_text or ""
    contract_text = contract_draft_text or ""
    notice = notice_text or ""
    spec_rows = _extract_goods_spec_table(tz_text)
    delivery_deadline = _match_first_dotall(
        tz_text,
        (
            r"Сроки поставки товара.*?1\s+2\s+1\s+(.+?)(?:\d+\.\s+[А-ЯA-ZЁ]|\Z)",
        ),
    ) or _extract_inline_goods_field(
        tz_text,
        ("Срок поставки", "Сроки поставки товара"),
        stop_markers=("Условия оплаты", "Адрес поставки", "Место поставки", "Условия поставки", "Порядок поставки"),
    )
    delivery_address = _match_first_dotall(
        tz_text,
        (
            r"Адрес поставки товара.*?1\s+2\s+1\s+(.+?)(?:\d+\.\s+[А-ЯA-ZЁ]|\Z)",
        ),
    ) or _extract_inline_goods_field(
        tz_text,
        ("Место поставки", "Место поставки товаров", "Адрес поставки товара"),
        stop_markers=("Условия поставки", "Срок поставки", "Сроки поставки товара", "Порядок поставки", "Условия оплаты"),
    )
    payment_terms = _match_first(
        contract_text,
        (
            r"в течение\s+(\d+\s*\([^)]+\)\s*рабочих дней[^.]+документа о приемке)",
            r"в течение\s+(\d+\s*рабочих дней[^.]+документа о приемке)",
            r"Оплата[^.]*?в течение\s+([^.]+)",
        ),
    )
    acceptance_window = _match_first(
        contract_text,
        (
            r"Не позднее\s+(\d+\s*\([^)]+\)\s*рабочих дней[^.]+документа о приемке)",
            r"Не позднее\s+(\d+\s*рабочих дней[^.]+документа о приемке)",
        ),
    )
    execution_security = _match_first(
        contract_text + "\n" + notice,
        (
            r"обеспечени[ея]\s+исполнения\s+контракта[^.]{0,120}",
        ),
    )
    execution_security_percent = _match_first_dotall(
        notice + "\n" + contract_text,
        (
            r"contractGuarantee[\s\S]{0,600}?<(?:\w+:)?part>(\d+(?:[.,]\d+)?)</(?:\w+:)?part>",
            r"обеспечени[ея]\s+исполнения\s+контракта[^%\n]{0,200}?(\d+(?:[.,]\d+)?)\s*%",
        ),
    )

    overview = [f"Предмет закупки: {metadata.get('tender_title') or 'поставка товаров'}"]
    if spec_rows:
        overview.append("В ТЗ выделена табличная спецификация по товарам.")
    if delivery_deadline:
        overview.append(f"Срок поставки: {(_normalize_analysis_sentence(delivery_deadline) or delivery_deadline).rstrip('.')}.")
    if delivery_address:
        overview.append(f"Адрес поставки: {(_normalize_analysis_sentence(delivery_address) or delivery_address).rstrip('.')}.")
    if payment_terms:
        short_payment_terms = _shorten_payment_terms(payment_terms)
        if short_payment_terms:
            overview.append(f"Оплата: {short_payment_terms.rstrip('.')}")
    overview = _dedupe_text_items([_normalize_analysis_sentence(item) or item for item in overview[:6]])

    compliance_highlights = [
        "Поставка должна полностью соответствовать характеристикам ТЗ и позициям спецификации.",
        "По товарам с КТРУ и обязательными параметрами нужно сверить неизменяемые характеристики.",
        "Перед подачей нужно проверить сертификаты, упаковку и условия поставки по каждой позиции.",
    ]
    delivery_model = _dedupe_text_items(
        [
            item
            for item in (
                _normalize_analysis_sentence(f"Поставка выполняется по адресу заказчика: {delivery_address}") if delivery_address else None,
                _normalize_analysis_sentence(f"Срок поставки: {delivery_deadline}") if delivery_deadline else None,
                "Разгрузка и логистика поставщика должны быть подтверждены отдельно.",
            )
            if item
        ]
    )
    contract_terms = []
    if payment_terms:
        contract_terms.append(f"Условия оплаты: в течение {payment_terms}.")
    if execution_security:
        security_text = "Обеспечение исполнения контракта: да"
        if execution_security_percent:
            security_text += f", {execution_security_percent.replace('.', ',')}% от НМЦК"
        contract_terms.append(security_text + ".")
    if acceptance_window:
        short_acceptance = _shorten_acceptance_terms(acceptance_window)
        if short_acceptance:
            contract_terms.append(f"Срок приемки: {short_acceptance.rstrip('.')}.")
    if "цена контракта является твердой" in contract_text.lower():
        contract_terms.append("Цена контракта: твердая, без индексации на период исполнения.")
    contract_terms = _dedupe_text_items([_normalize_analysis_sentence(item) or item for item in contract_terms[:6]])

    next_actions = _dedupe_text_items(
        [
            "Сверить таблицу ТЗ с исходным приложением и проверить количество по каждой позиции.",
            "Подтвердить наличие товара или сроки поставки у поставщиков по критичным позициям.",
            "До запроса ТКП проверить обязательные сертификаты, упаковку и требования к доставке.",
        ]
    )
    return {
        "overview": overview,
        "compliance_highlights": compliance_highlights,
        "delivery_model": delivery_model,
        "contract_highlights": contract_terms,
        "next_actions": next_actions,
        "extracted_fields": ["спецификация", "срок поставки", "адрес поставки"] if spec_rows else ["срок поставки"],
        "procurement_kind": "goods",
        "spec_table": {
            "columns": ["№", "Наименование", "Ед. изм.", "Кол-во", "Характеристики"],
            "rows": spec_rows,
        },
    }


def _build_preliminary_procurement_analysis(
    *,
    metadata: dict[str, Any],
    technical_spec_text: str,
    contract_draft_text: str,
    notice_text: str,
) -> dict[str, Any]:
    tz_text = technical_spec_text or ""
    contract_text = contract_draft_text or ""
    notice = notice_text or ""
    combined = "\n".join(part for part in (tz_text, contract_text, notice) if part)
    procurement_kind = _infer_procurement_kind(tz_text, contract_text, notice, str(metadata.get("tender_title") or ""))
    if procurement_kind == "goods":
        return _build_goods_preliminary_analysis(
            metadata=metadata,
            technical_spec_text=technical_spec_text,
            contract_draft_text=contract_draft_text,
            notice_text=notice_text,
        )

    service_subject = _match_first(
        tz_text,
        (
            r"1\.\s*Наименование и описание услуг:\s*(.+?)(?:\n\d+\.|\Z)",
            r"Объект закупки\s*[:\-]?\s*(.+?)(?:\n|$)",
            r"Описание объекта закупки\s*[:\-]?\s*(.+?)(?:\n|$)",
        ),
    ) or metadata.get("tender_title")
    training_format = _match_first(
        tz_text,
        (
            r"\b(Очно-заочная(?:\s*\([^)]+\))?)\b",
            r"\b(Очная(?:\s*\([^)]+\))?)\b",
            r"\b(Заочная(?:\s*\([^)]+\))?)\b",
            r"Форма обучения\s*\n\s*([^\n]+)",
            r"Форма обучения\s*[:\-]?\s*([^\n]+)",
        ),
    )
    hours = _match_first(
        tz_text,
        (
            r"(\d+\s*час(?:ов|а)?)",
        ),
    )
    listeners = _match_first(
        tz_text,
        (
            r"\b\d+\s*час(?:ов|а)?\s*\n\s*(\d+)\b",
            r"Кол-во слушателей.*?\n.*?\n.*?\n.*?\n.*?\n\s*(\d+)",
            r"(\d+)\s*\(?[а-я]*\)?\s*человек",
            r"слушател[^\n]*?(\d+)",
        ),
    )
    service_deadline = _match_first(
        tz_text,
        (
            r"не позднее\s+(\d{1,2}\s+[А-Яа-яЁё]+\s+\d{4}\s+года)",
            r"не позднее\s+([^.\\n]+)",
            r"Сроки оказания Услуг\s*[–-]\s*([^.\\n]+)",
        ),
    )
    location = _match_first(
        tz_text,
        (
            r"3\.\s*Место оказания услуг:\s*(.+?)(?:\n\d+\.|\Z)",
            r"Место оказания Услуг:\s*(.+?)(?:\n\d+\.|\Z)",
        ),
    )
    payment_terms = _match_first(
        contract_text,
        (
            r"в течение\s+(\d+\s*\([^)]+\)\s*рабочих дней[^.]+документа о приемке)",
            r"в течение\s+(\d+\s*рабочих дней[^.]+документа о приемке)",
            r"Оплата[^.]*?в течение\s+([^.]+)",
        ),
    )
    execution_security = _match_first(
        contract_text + "\n" + notice,
        (
            r"обеспечени[ея]\s+исполнения\s+контракта[^.]{0,120}",
        ),
    )
    if not execution_security and "исполнения контракта" in contract_text.lower() and "обеспеч" in contract_text.lower():
        execution_security = "обеспечение исполнения контракта"
    execution_security_percent = _match_first_dotall(
        notice + "\n" + contract_text,
        (
            r"contractGuarantee[\s\S]{0,600}?<(?:\w+:)?part>(\d+(?:[.,]\d+)?)</(?:\w+:)?part>",
            r"обеспечени[ея]\s+исполнения\s+контракта[^%\n]{0,200}?(\d+(?:[.,]\d+)?)\s*%",
        ),
    )
    execution_security_amount = _match_first_dotall(
        notice + "\n" + contract_text,
        (
            r"contractGuarantee[\s\S]{0,600}?<(?:\w+:)?amount>(\d+(?:[.,]\d+)?)</(?:\w+:)?amount>",
            r"обеспечени[ея]\s+исполнения\s+контракта[^\\d]{0,200}?([\d\s]+(?:[.,]\d+)?)\s*руб",
        ),
    )
    acceptance_window = _match_first(
        contract_text,
        (
            r"Не позднее\s+(\d+\s*\([^)]+\)\s*рабочих дней[^.]+документа о приемке)",
            r"Не позднее\s+(\d+\s*рабочих дней[^.]+документа о приемке)",
        ),
    )
    unilateral_termination = _match_first(
        contract_text,
        (
            r"(Заказчик вправе принять решение об одностороннем отказе[^.]+)",
            r"(одностороннем отказе от исполнения Контракта[^.]+)",
        ),
    )

    compliance_highlights = _collect_matches(
        tz_text,
        (
            r"(согласован[^\n.]*Федеральной службой по техническому и экспортному контролю[^\n.]*)",
            r"(выдать удостоверени[^\n.]*повышении квалификации[^\n.]*)",
            r"(итогов[^\n.]*аттестаци[^\n.]*)",
            r"(учебный план должен содержать[^\n.]*)",
            r"(раздаточн[^\n.]*материал[^\n.]*)",
            r"(ГОСТ\s*\d+(?:-\d+)?[^\n.]*)",
        ),
        limit=6,
    )
    delivery_model = _collect_matches(
        tz_text,
        (
            r"(Очно-заочная[^\n.]*)",
            r"(с применением дистанционных образовательных технологий[^\n.]*)",
            r"(60\s*%\s*времени[^\n.]*)",
            r"(40\s*%\s*времени[^\n.]*)",
            r"(с 09\.00 до 18\.00[^\n.]*)",
            r"(в городе [А-ЯЁA-Z][^;.\n]*)",
        ),
        limit=6,
    )

    extracted_fields = [
        label
        for label, value in (
            ("предмет закупки", service_subject),
            ("формат оказания услуг", training_format),
            ("объём программы", hours),
            ("количество слушателей", listeners),
            ("срок оказания услуг", service_deadline),
            ("место оказания услуг", location),
            ("условия оплаты", payment_terms),
            ("приёмка", acceptance_window),
        )
        if value
    ]

    overview: list[str] = []
    if service_subject:
        overview.append(f"Предмет закупки: {service_subject}")
    if training_format:
        overview.append(f"Формат: {training_format}")
    if hours or listeners:
        overview.append(
            "Объём: "
            + ", ".join(
                part
                for part in (
                    hours,
                    f"{listeners} слушателей" if listeners and listeners.isdigit() else listeners,
                )
                if part
            )
        )
    if service_deadline:
        overview.append(f"Срок оказания услуг: {service_deadline}")
    if location:
        overview.append(f"Место оказания услуг: {location}")
    if payment_terms:
        short_payment_terms = _shorten_payment_terms(payment_terms)
        if short_payment_terms:
            overview.append(f"Оплата: {short_payment_terms.rstrip('.')}")

    overview = _dedupe_text_items([_normalize_analysis_sentence(item) or item for item in overview[:6]])
    compliance_highlights = [
        rewritten
        for rewritten in (_rewrite_compliance_highlight(item) for item in compliance_highlights[:6])
        if rewritten
    ]
    compliance_highlights = _dedupe_text_items(compliance_highlights)
    delivery_model = [
        rewritten
        for rewritten in (_rewrite_delivery_model_item(item, procurement_kind) for item in delivery_model[:6])
        if rewritten
    ]
    delivery_model = _dedupe_text_items(delivery_model)

    next_actions = [
        "Проверить, можем ли мы обеспечить очную часть в Хабаровске и дистанционную часть в требуемом формате."
        if location or training_format
        else "Подтвердить реальный формат оказания услуг и локацию исполнения.",
        "Подтвердить наличие согласованной с ФСТЭК программы и право выдачи удостоверения о повышении квалификации."
        if any("Федеральной службой по техническому и экспортному контролю" in item for item in compliance_highlights)
        else "Проверить обязательные допуски, программу и итоговые документы по обучению.",
        "До запроса ТКП уточнить ресурсы: график, преподаватели, аудитории, оборудование и учебные материалы.",
    ]
    next_actions = _dedupe_text_items([_normalize_analysis_sentence(item) or item for item in next_actions[:4]])

    contract_terms: list[str] = []
    if payment_terms:
        contract_terms.append(f"Условия оплаты: в течение {payment_terms}.")
    if execution_security:
        security_parts: list[str] = ["Обеспечение исполнения контракта: да"]
        if execution_security_percent:
            security_parts.append(f"{execution_security_percent.replace('.', ',')}% от НМЦК")
        if execution_security_amount:
            amount_text = _format_money_value(execution_security_amount)
            if amount_text:
                security_parts.append(f"{amount_text} руб.")
        contract_terms.append(", ".join(security_parts) + ".")
    if acceptance_window:
        short_acceptance = _shorten_acceptance_terms(acceptance_window)
        if short_acceptance:
            contract_terms.append(f"Срок приемки: {short_acceptance.rstrip('.')}.")
    if "цена контракта является твердой" in contract_text.lower():
        contract_terms.append("Цена контракта: твердая, без индексации на период исполнения.")
    if unilateral_termination:
        contract_terms.append("Односторонний отказ от исполнения контракта предусмотрен по основаниям, указанным в договоре.")
    contract_terms = _dedupe_text_items([_normalize_analysis_sentence(item) or item for item in contract_terms[:6]])

    return {
        "overview": overview[:6],
        "compliance_highlights": compliance_highlights[:6],
        "delivery_model": delivery_model[:6],
        "contract_highlights": contract_terms[:6],
        "next_actions": next_actions[:4],
        "extracted_fields": extracted_fields[:8],
        "procurement_kind": procurement_kind,
    }


def _normalize_supplier_questions(questions: list[dict[str, Any]], procurement_kind: str) -> list[str]:
    if procurement_kind != "services":
        return [_translate_user_text(item["question"]) for item in questions[:8]]
    service_questions = {
        "spec_match": "Подтверждаете ли вы оказание услуг в полном объеме по техническому заданию?",
        "price": "Какова стоимость услуг с НДС и без НДС?",
        "delivery": "Какие организационные расходы входят в стоимость услуг?",
        "delivery_time": "Подтверждаете ли вы сроки оказания услуг по графику заказчика?",
        "availability": "Есть ли у вас преподаватели, аудитории и ресурсы на требуемые даты?",
        "certificates": "Есть ли документы и согласования, подтверждающие право на оказание этих услуг?",
        "warranty": "Какие итоговые документы и результаты обучения вы обеспечиваете по завершении программы?",
        "analog": "Есть ли отклонения от программы, формата или состава услуг, указанных в ТЗ?",
        "payment": "Какие условия оплаты вы готовы подтвердить со своей стороны?",
        "validity": "Какой срок действия вашего коммерческого предложения?",
        "installation": "Что входит в организацию очной части обучения на вашей площадке?",
        "logistics": "Входят ли в стоимость раздаточные материалы, дистанционная платформа и организационное сопровождение?",
    }
    normalized: list[str] = []
    seen: set[str] = set()
    for item in questions:
        category = str(item.get("category") or "").strip()
        question = service_questions.get(category) or _translate_user_text(item["question"])
        if question in seen:
            continue
        seen.add(question)
        normalized.append(question)
        if len(normalized) >= 8:
            break
    return normalized


def _build_output_payloads(
    *,
    metadata: dict[str, Any],
    documents: list[AnalyzedDocument],
    analysis_mode: str,
    requirements: dict[str, Any],
    calibrated_risks: list[dict[str, Any]],
    supplier_questions: list[dict[str, Any]],
    tkp_comparison: dict[str, Any] | None,
    economics: dict[str, Any] | None,
    bid_decision: dict[str, Any] | None,
    core_complete: bool,
) -> dict[str, dict[str, Any]]:
    technical_spec_text = _collect_role_text(documents, "technical_spec")
    contract_draft_text = _collect_role_text(documents, "contract_draft")
    notice_text = _collect_role_text(documents, "notice") or _collect_role_text(documents, "supporting") or metadata["tender_title"]
    procurement_kind = _infer_procurement_kind(
        technical_spec_text,
        contract_draft_text,
        notice_text,
        str(metadata.get("tender_title") or ""),
    )
    requirement_rows = _extract_requirement_rows(requirements, core_complete, procurement_kind)
    quote_files_present = bool(tkp_comparison and tkp_comparison.get("suppliers"))
    output_warnings = list(metadata.get("warnings", []))
    preliminary_analysis = _build_preliminary_procurement_analysis(
        metadata=metadata,
        technical_spec_text=technical_spec_text,
        contract_draft_text=contract_draft_text,
        notice_text=notice_text,
    )

    tender_summary = {
        "run_id": metadata["run_id"],
        "prepared_at": _safe_datetime(),
        "title": metadata["tender_title"],
        "procedure_type": "Поиск закупки + intake" if metadata.get("mode") == "procurement_search_intake" else "Загруженный demo run",
        "customer": metadata["customer_name"],
        "category": metadata["tender_category"],
        "submission_deadline": _safe_datetime(),
        "analysis_status": metadata["status"],
        "procurement_code": metadata.get("procurement_id") or metadata["run_id"].upper(),
        "documents": [
            {
                "name": doc.display_name,
                "role": doc.role,
                "pages": 1,
            }
            for doc in documents
        ],
        "document_signals": [
            f"Режим создания run: {metadata.get('mode', 'uploaded_demo')}.",
            f"Загружено файлов: {len(metadata.get('files', []))}.",
            f"Файлов с извлечённым текстом: {len([doc for doc in documents if doc.text])}.",
            f"Режим анализа: {analysis_mode}.",
        ],
        "preliminary_analysis": preliminary_analysis,
    }

    requirements_payload = {
        "requirements": requirement_rows,
        "preliminary_analysis": preliminary_analysis,
        "manual_review_points": [
            "Проверить корректность распределения документов по ролям.",
            "Подтвердить ключевые требования по исходным документам перед внешними действиями.",
        ],
    }

    supplier_questions_payload = {
        "ambiguities": [
            "Часть требований получена из ограниченного demo-parsing.",
            "Параметры оплаты и допустимость аналогов требуют ручной валидации.",
        ],
        "questions": _normalize_supplier_questions(supplier_questions, procurement_kind),
        "manual_checks": [
            "Согласовать финальный вопросник с оператором.",
            "Не отправлять вопросы поставщикам автоматически из этого интерфейса.",
        ],
    }

    rfq_payload = {
        "rfq_title": f"RFQ draft / {metadata['tender_title']}",
        "sections": [
            "Перечень позиций и объём поставки",
            "Подтверждение сроков, сертификатов и гарантий",
            "Условия оплаты и срок действия КП",
            "Таблица для аналогов и замечаний поставщика",
        ],
        "supplier_targets": [item.get("supplier_label", "Поставщик") for item in (tkp_comparison or {}).get("suppliers", [])] or [
            "Поставщик 1",
            "Поставщик 2",
            "Поставщик 3",
        ],
        "manual_checks": [
            "Проверить RFQ на соответствие исходной закупке.",
            "Отправка RFQ выполняется только человеком вне этого demo UI.",
        ],
    }

    quotes_payload = {
        "status": tkp_comparison.get("status", "blocked") if tkp_comparison else "blocked",
        "analysis_mode": tkp_comparison.get("analysis_mode", analysis_mode) if tkp_comparison else analysis_mode,
        "supplier_quotes_found": tkp_comparison.get("supplier_quotes_found", 0) if tkp_comparison else 0,
        "items_extracted": tkp_comparison.get("items_extracted", 0) if tkp_comparison else 0,
        "suppliers": tkp_comparison.get("suppliers", []) if tkp_comparison else [],
        "items": tkp_comparison.get("items", []) if tkp_comparison else [],
        "comparison_summary": tkp_comparison.get("comparison_summary", {}) if tkp_comparison else {},
        "warnings": tkp_comparison.get("warnings", []) if tkp_comparison else [],
        "limitations": tkp_comparison.get("limitations", []) if tkp_comparison else [],
        "highlights": (
            [
                f"Найдено распознанных ТКП: {tkp_comparison.get('supplier_quotes_found', 0)}.",
                f"Извлечено сопоставимых позиций: {tkp_comparison.get('items_extracted', 0)}.",
                "Сравнение выполнено локально, в детерминированном демо-режиме без внешних действий.",
            ]
            if quote_files_present
            else [
                "ТКП не загружены или не распознаны как структурированные таблицы.",
                "Агент подготовил RFQ и список вопросов для дальнейшей ручной работы.",
            ]
        ),
        "manual_checks": (
            [item.get("message", "") for item in tkp_comparison.get("manual_checks", [])]
            if tkp_comparison
            else []
        )
        or (
            ["Проверить реальные значения цены, срока и гарантий по загруженным ТКП."]
            if quote_files_present
            else ["Собрать ТКП вручную и повторно запустить анализ после загрузки коммерческих предложений."]
        ),
    }

    economics_payload = {
        "analysis_mode": economics.get("analysis_mode", analysis_mode) if economics else analysis_mode,
        "currency": economics.get("currency", "RUB") if economics else "RUB",
        "economics_status": economics.get("economics_status", "insufficient_data") if economics else "insufficient_data",
        "supplier_cost_min": economics.get("supplier_cost_min") if economics else None,
        "supplier_cost_selected": economics.get("supplier_cost_selected") if economics else None,
        "expected_revenue": economics.get("expected_revenue") if economics else None,
        "preliminary_bid_price": economics.get("preliminary_bid_price") if economics else None,
        "gross_margin_amount": economics.get("gross_margin_amount") if economics else None,
        "gross_margin_percent": economics.get("gross_margin_percent") if economics else None,
        "logistics_reserve": economics.get("logistics_reserve") if economics else None,
        "risk_reserve": economics.get("risk_reserve") if economics else None,
        "payment_delay_days": economics.get("payment_delay_days") if economics else None,
        "cash_gap_estimate": economics.get("cash_gap_estimate") if economics else None,
        "selected_supplier_name": economics.get("selected_supplier_name") if economics else None,
        "result": (
            "Недостаточно данных для полной экономики"
            if not economics
            else (
                "Экономика выглядит условно приемлемой"
                if economics.get("economics_status") == "conditionally_viable"
                else "Экономика требует ручной проверки"
            )
        ),
        "status": economics.get("status", "blocked") if economics else "blocked",
        "metrics": [
            {"label": "Минимальная закупочная стоимость", "value": economics.get("supplier_cost_min", "unknown") if economics else "unknown"},
            {"label": "Выбранная закупочная стоимость", "value": economics.get("supplier_cost_selected", "unknown") if economics else "unknown"},
            {"label": "Резерв логистики", "value": economics.get("logistics_reserve", "unknown") if economics else "unknown"},
            {"label": "Резерв риска", "value": economics.get("risk_reserve", "unknown") if economics else "unknown"},
            {"label": "Целевая маржа", "value": f"{economics.get('gross_margin_percent')}%" if economics and economics.get("gross_margin_percent") is not None else "unknown"},
            {"label": "Предварительная цена подачи", "value": economics.get("preliminary_bid_price", "unknown") if economics else "unknown"},
            {"label": "Оценка кассового разрыва", "value": economics.get("cash_gap_estimate", "unknown") if economics else "unknown"},
        ],
        "drivers": (
            [
                f"Выбран поставщик: {economics.get('selected_supplier_name') or 'не определён'}.",
                "Ожидаемая выручка не рассчитывается автоматически без цены заказчика.",
                "Расчёт построен на локальных ТКП и операторских параметрах из демо-формы.",
            ]
            if economics
            else ["Без структурированных цен экономика не может быть автоматически признана полной."]
        ),
        "manual_checks": ([item.get("message", "") for item in economics.get("manual_checks", [])] if economics else [])
        or ["Сверить фактические цены, логистику и резерв вручную."],
        "warnings": economics.get("warnings", []) if economics else [],
        "limitations": economics.get("limitations", []) if economics else [],
        "assumptions": economics.get("assumptions", {}) if economics else {},
    }

    risks_payload = {
        "summary": "Найдены ограничения и риски, требующие ручной проверки.",
        "risks": [
            {
                "risk": _translate_user_text(risk.get("clause", "Ограничение")),
                "severity": "needs_review" if risk.get("classification") == "deal_breaker_candidate" else "warning",
                "impact": _translate_user_text(risk.get("impact", "")),
                "mitigation": _translate_user_text(risk.get("mitigation", "")),
            }
            for risk in calibrated_risks
        ]
        or [
            {
                "risk": "Недостаточно данных по договорным условиям",
                "severity": "needs_review",
                "impact": "Часть контрактных рисков не может быть оценена автоматически.",
                "mitigation": "Проверить договор и комплектность вручную.",
            }
        ],
        "manual_checks": [
            "Проверить договорные ограничения и совместимость аналогов вручную."
        ],
    }

    economics_ready = bool(economics and economics.get("economics_status") in {"conditionally_viable", "viable"})
    if core_complete and quote_files_present and economics_ready:
        recommendation = DemoRecommendationCode.PARTICIPATE_CONDITIONALLY
        label = "участвовать условно"
        rationale = [
            "Базовый контролируемый путь раннера выполнен на локально загруженных документах.",
            "ТКП структурированы и сопоставлены в локальном deterministic parser слое.",
            "Экономика выглядит условно приемлемой, но решение всё ещё требует проверки оператором.",
            "Рекомендация остаётся предварительной и не заменяет решение человека.",
        ]
    else:
        recommendation = DemoRecommendationCode.MANUAL_REVIEW_REQUIRED
        label = "нужна ручная проверка"
        rationale = [
            "Данных недостаточно для безусловной рекомендации.",
            "Часть шагов выполнена в fallback-режиме или заблокирована отсутствием ТКП или извлечённого текста.",
            "Следующее действие должен подтвердить оператор.",
        ]

    final_recommendation = {
        "recommendation": recommendation.value,
        "label": label,
        "rationale": rationale,
        "key_requirements": [item["title"] for item in requirement_rows[:4]] or ["Проверка комплектности документов"],
        "open_questions": supplier_questions_payload["questions"][:3],
        "risks": [item["risk"] for item in risks_payload["risks"][:4]],
        "economics": [f"{item['label']}: {item['value']}" for item in economics_payload["metrics"]],
        "manual_checks": [
            "Проверить исходные документы и роли файлов.",
            "Подтвердить RFQ и вопросы перед внешними коммуникациями.",
            "Проверить нормализацию Excel-таблиц и сопоставление позиций перед финансовым решением.",
            "Сделать финальное решение только после ручной проверки.",
        ],
    }

    trace = {
        "documents_considered": [doc.display_name for doc in documents],
        "procurement_context": {
            "source": metadata.get("procurement_source"),
            "procurement_id": metadata.get("procurement_id"),
            "procurement_url": metadata.get("procurement_url"),
            "attachments_status": metadata.get("attachments_status"),
        },
        "fields_extracted": [
            *preliminary_analysis.get("extracted_fields", []),
        ],
        "risk_signals": [
            "Режим анализа ограничен локальным контролируемым адаптером.",
            "Внешние действия отключены по design policy.",
            "Нормализация Excel-таблиц использует deterministic parser + heuristics без LLM.",
            "Часть выводов требует ручного подтверждения по исходным файлам.",
        ],
        "decision_factors": rationale,
        "overall_explanation": (
            "Агент использовал только локально загруженные файлы, безопасное извлечение текста и контролируемый адаптер раннера или fallback-адаптер. "
            "Если комплект документов или ТКП неполный, интерфейс честно показывает блокировки и необходимость ручной проверки вместо ложной полной автоматизации."
        ),
        "per_step": {
            "documents": "Файлы сохранены локально, имена нормализованы, опасные пути отброшены.",
            "requirements": "Требования и предварительный анализ собраны из ТЗ, извещения и проекта договора с безопасным локальным извлечением текста.",
            "questions": "Сформирован список вопросов для ручной коммуникации с поставщиками.",
            "rfq": "Подготовлен draft RFQ для ручной отправки вне системы.",
            "quotes": "Сравнение ТКП использует детерминированный парсер таблиц и честно помечает частичные результаты и зоны ручной проверки.",
            "economics": "Экономика строится только на доступных локальных данных и операторских параметрах, без выдуманной выручки.",
            "risks": "Риски агрегированы из доступного контракта и ограничений demo-mode.",
            "decision": "Итог всегда требует подтверждения человеком и не приводит к внешним действиям.",
        },
        "human_control_note": "Демо- и пилотный режим. Нет подачи заявок, писем, ЭЦП или действий на площадках без человека.",
        "limitations": metadata.get("limitations", []) + output_warnings,
    }

    return {
        "tender_summary": tender_summary,
        "requirements": requirements_payload,
        "supplier_questions": supplier_questions_payload,
        "rfq_draft": rfq_payload,
        "quotes_comparison": quotes_payload,
        "economics": economics_payload,
        "contract_risks": risks_payload,
        "final_recommendation": final_recommendation,
        "trace": trace,
    }


def _build_steps_from_outputs(metadata: dict[str, Any], outputs: dict[str, dict[str, Any]]) -> list[DemoStep]:
    requirements = outputs["requirements"]
    questions = outputs["supplier_questions"]
    rfq = outputs["rfq_draft"]
    quotes = outputs["quotes_comparison"]
    economics = outputs["economics"]
    risks = outputs["contract_risks"]
    final_recommendation = outputs["final_recommendation"]
    trace = outputs["trace"]["per_step"]

    quote_blocked = quotes["status"] == "blocked"
    quote_partial = quotes["status"] in {"partial", "needs_review"}
    economics_blocked = economics["status"] == "blocked"
    economics_partial = economics["status"] in {"partial", "needs_review"}
    core_limitations = outputs["trace"].get("limitations", [])
    partial_requirements = any("fallback" in item.lower() for item in core_limitations)
    file_count = len(metadata.get("files", []))
    docs_status = DemoStepStatus.DONE if file_count else DemoStepStatus.BLOCKED
    preliminary_analysis = requirements.get("preliminary_analysis", {})

    steps: list[DemoStep] = []
    if metadata.get("procurement_source"):
        procurement_title = metadata.get("tender_title", "Закупка")
        procurement_findings = [
            f"Источник: {metadata.get('procurement_source')}.",
            f"Идентификатор закупки: {metadata.get('procurement_id') or 'не указан'}.",
            f"Статус документации: {metadata.get('attachments_status') or 'не определён'}.",
        ]
        if metadata.get("procurement_url"):
            procurement_findings.append(f"Карточка закупки: {metadata.get('procurement_url')}.")
        steps.append(
            DemoStep(
                key="procurement_search",
                order=0,
                title="Поиск закупки",
                short_title="Поиск закупки",
                status=DemoStepStatus.DONE,
                description="Read-only поиск закупки и выбор карточки оператором.",
                agent_action=f"Найдена и выбрана закупка '{procurement_title}' из безопасного procurement discovery слоя.",
                result_summary=f"Выбрана закупка {metadata.get('procurement_id') or metadata.get('run_id')}.",
                findings=procurement_findings,
                human_review=[
                    "Проверить релевантность найденной закупки перед продолжением.",
                    "Подтвердить, что источник не требует авторизации, если будет подключаться реальный коннектор.",
                ],
                trace="Поиск выполнялся в безопасном режиме только чтения без авторизации, обхода captcha и внешних действий.",
                result_sections=[
                    DemoDetailSection(
                        title="Контекст поиска",
                        kind="bullets",
                        items=[
                            f"Запрос: {metadata.get('procurement_query') or 'не указан'}",
                            f"Источник: {metadata.get('procurement_source')}",
                            f"Статус документации: {metadata.get('attachments_status') or 'не определён'}",
                        ],
                    )
                ],
            )
        )

    steps.extend([
        DemoStep(
            key="documents",
            order=1,
            title="Документы",
            short_title="Документы",
            status=docs_status,
            description="Локальная загрузка и безопасная подготовка файлов к анализу.",
            agent_action="Файлы сохранены в локальную demo-run директорию, имена нормализованы, опасные пути удалены.",
            result_summary=(
                f"Загружено {file_count} файлов."
                if file_count
                else "Документы ещё не загружены. Для продолжения нужен ручной upload."
            ),
            findings=[item["display_name"] for item in metadata.get("files", [])]
            or ["Автоматически доступных документов нет, требуется ручная загрузка."],
            human_review=[
                "Проверить, что каждому файлу назначена корректная роль."
            ]
            if file_count
            else ["Загрузить документацию вручную и только потом запускать анализ."],
            trace=trace["documents"],
            result_sections=[
                DemoDetailSection(
                    title="Загруженные файлы",
                    kind="table",
                    columns=["Файл", "Расширение", "Размер"],
                    rows=[
                        {
                            "Файл": item["display_name"],
                            "Расширение": item["extension"],
                            "Размер": f"{item['size_bytes']} bytes",
                        }
                        for item in metadata.get("files", [])
                    ],
                )
            ],
        ),
        DemoStep(
            key="requirements",
            order=2,
            title="Требования",
            short_title="Требования",
            status=DemoStepStatus.PARTIAL if partial_requirements else DemoStepStatus.DONE,
            description="Извлечение ключевых требований и обязательных документов из доступного локального пакета.",
            agent_action="Собран снимок требований с помощью контролируемого парсера и fallback-адаптера.",
            result_summary=(
                preliminary_analysis.get("overview", [f"Выделено требований: {len(requirements['requirements'])}."])[0]
                if preliminary_analysis.get("overview")
                else f"Выделено требований: {len(requirements['requirements'])}."
            ),
            findings=(preliminary_analysis.get("overview", []) + [item["title"] for item in requirements["requirements"]])[:10],
            human_review=requirements["manual_review_points"],
            trace=trace["requirements"],
            result_sections=[
                DemoDetailSection(
                    title="Предварительный анализ закупки",
                    kind="bullets",
                    items=(
                        preliminary_analysis.get("overview", [])
                        + preliminary_analysis.get("compliance_highlights", [])[:3]
                        + preliminary_analysis.get("contract_highlights", [])[:2]
                    )[:10],
                ),
                DemoDetailSection(
                    title="Требования",
                    kind="table",
                    columns=["Требование", "Деталь", "Источник"],
                    rows=[
                        {
                            "Требование": item["title"],
                            "Деталь": item["detail"],
                            "Источник": item["source"],
                        }
                        for item in requirements["requirements"]
                    ],
                )
            ],
        ),
        DemoStep(
            key="supplier_search",
            order=3,
            title="Поиск поставщиков",
            short_title="Поставщики",
            status=DemoStepStatus.DONE if metadata.get("supplier_search", {}).get("suppliers") else DemoStepStatus.PARTIAL,
            description="Интернет-поиск потенциальных поставщиков через Yandex Search API.",
            agent_action="Выполнен поиск поставщиков на основе требований закупки.",
            result_summary=f"Найдено поставщиков: {metadata.get('supplier_search', {}).get('total_found', 0)}." if metadata.get("supplier_search", {}).get("suppliers") else "Поиск поставщиков не выполнялся или не настроен.",
            findings=[f"{s['name']} — {s['site']}" for s in metadata.get("supplier_search", {}).get("suppliers", [])[:5]],
            human_review=["Проверить найденных поставщиков вручную перед отправкой RFQ."],
            trace=trace.get("supplier_search", "Поиск поставщиков выполнен через Yandex Search API без внешних изменений."),
            result_sections=[
                DemoDetailSection(
                    title="Найденные поставщики",
                    kind="table",
                    columns=["Поставщик", "Сайт", "Сигналы"],
                    rows=[
                        {"Поставщик": s["name"], "Сайт": s["site"], "Сигналы": ", ".join(s.get("signals", []) or ["—"])}
                        for s in metadata.get("supplier_search", {}).get("suppliers", [])[:10]
                    ],
                )
                if metadata.get("supplier_search", {}).get("suppliers")
                else DemoDetailSection(title="Статус поиска", kind="bullets", items=[
                    metadata.get("supplier_search", {}).get("query", "Поиск не выполнялся"),
                    f"Поставщиков не найдено или API не настроено.",
                ]),
            ],
        ),
        DemoStep(
            key="questions",
            order=4,
            title="Вопросы",
            short_title="Вопросы",
            status=DemoStepStatus.NEEDS_REVIEW,
            description="Формирование вопросника по неоднозначностям и отсутствующим данным.",
            agent_action="Подготовлен набор вопросов для RFQ под контролем оператора.",
            result_summary=f"Подготовлено вопросов: {len(questions['questions'])}.",
            findings=questions["ambiguities"],
            human_review=questions["manual_checks"],
            trace=trace["questions"],
            result_sections=[
                DemoDetailSection(title="Вопросы поставщикам", kind="bullets", items=questions["questions"])
            ],
        ),
        DemoStep(
            key="rfq",
            order=5,
            title="RFQ",
            short_title="RFQ",
            status=DemoStepStatus.DONE if requirements["requirements"] else DemoStepStatus.PARTIAL,
            description="Подготовка draft RFQ для ручной отправки.",
            agent_action="Сформирован черновик RFQ на основе извлечённых требований и вопросов поставщикам.",
            result_summary="RFQ готов как внутренний черновик.",
            findings=rfq["sections"],
            human_review=rfq["manual_checks"],
            trace=trace["rfq"],
            result_sections=[DemoDetailSection(title="Секции RFQ", kind="bullets", items=rfq["sections"])],
        ),
        DemoStep(
            key="quotes",
            order=6,
            title="ТКП",
            short_title="ТКП",
            status=DemoStepStatus.BLOCKED if quote_blocked else (DemoStepStatus.PARTIAL if quote_partial else DemoStepStatus.DONE),
            description="Сопоставление коммерческих предложений, если они были загружены.",
            agent_action="Проверено наличие ТКП и собран локальный снимок сравнения с нормализацией таблиц.",
            result_summary="ТКП не загружены." if quote_blocked else f"Найдено ТКП: {quotes.get('supplier_quotes_found', 0)}, позиций: {quotes.get('items_extracted', 0)}.",
            findings=quotes["highlights"],
            human_review=quotes["manual_checks"],
            trace=trace["quotes"],
            result_sections=[
                DemoDetailSection(
                    title="Извлечённые ТКП",
                    kind="table",
                    columns=["Поставщик", "Файл", "Сумма", "Валюта", "Позиций", "Уверенность"],
                    rows=[
                        {
                            "Поставщик": item.get("supplier_name", "Поставщик"),
                            "Файл": item.get("source_file", "unknown"),
                            "Сумма": item.get("total_amount", "unknown"),
                            "Валюта": item.get("currency", "unknown"),
                            "Позиций": item.get("items_count", "unknown"),
                            "Уверенность": item.get("price_confidence", "unknown"),
                        }
                        for item in quotes["suppliers"]
                    ],
                )
                if quotes["suppliers"]
                else DemoDetailSection(title="Статус ТКП", kind="bullets", items=quotes["highlights"]),
                DemoDetailSection(
                    title="Сравнение предложений",
                    kind="table",
                    columns=["Позиция", "Лучшая цена", "Разброс %", "Нужна проверка"],
                    rows=[
                        {
                            "Позиция": item.get("normalized_name", "unknown"),
                            "Лучшая цена": item.get("best_price_supplier", "unknown"),
                            "Разброс %": item.get("price_spread_percent", "unknown"),
                            "Нужна проверка": "да" if item.get("needs_review") else "нет",
                        }
                        for item in quotes.get("items", [])[:20]
                    ],
                )
                if quotes["suppliers"]
                else DemoDetailSection(title="Статус ТКП", kind="bullets", items=quotes["highlights"])
            ],
        ),
        DemoStep(
            key="economics",
            order=7,
            title="Экономика",
            short_title="Экономика",
            status=DemoStepStatus.BLOCKED if economics_blocked else (DemoStepStatus.PARTIAL if economics_partial else DemoStepStatus.NEEDS_REVIEW),
            description="Расчёт экономики только по доступным локальным данным.",
            agent_action="Собран снимок экономики без притворства полной автоматизации при нехватке данных.",
            result_summary=economics["result"],
            findings=economics["drivers"],
            human_review=economics["manual_checks"],
            trace=trace["economics"],
            result_sections=[
                DemoDetailSection(
                    title="Снимок экономики",
                    kind="table",
                    columns=["Показатель", "Значение"],
                    rows=[
                        {"Показатель": item["label"], "Значение": item["value"]}
                        for item in economics["metrics"]
                    ],
                )
            ],
        ),
        DemoStep(
            key="risks",
            order=9,
            title="Риски",
            short_title="Риски",
            status=DemoStepStatus.WARNING,
            description="Сводка рисков и ограничений demo-mode.",
            agent_action="Риски агрегированы в единый блок для удобной ручной проверки.",
            result_summary=risks["summary"],
            findings=[item["risk"] for item in risks["risks"]],
            human_review=risks["manual_checks"],
            trace=trace["risks"],
            result_sections=[
                DemoDetailSection(
                    title="Риски",
                    kind="table",
                    columns=["Риск", "Серьёзность", "Влияние", "Смягчение"],
                    rows=[
                        {
                            "Риск": item["risk"],
                            "Серьёзность": item["severity"],
                            "Влияние": item["impact"],
                            "Смягчение": item["mitigation"],
                        }
                        for item in risks["risks"]
                    ],
                )
            ],
        ),
        DemoStep(
            key="decision",
            order=9,
            title="Решение",
            short_title="Решение",
            status=DemoStepStatus.NEEDS_REVIEW,
            description="Предварительная рекомендация без внешних действий и без снятия human control.",
            agent_action="Собран итоговый блок рекомендации с открытыми вопросами и ручными проверками.",
            result_summary=f"Рекомендация: {final_recommendation['label']}.",
            findings=final_recommendation["rationale"],
            human_review=final_recommendation["manual_checks"],
            trace=trace["decision"],
            result_sections=[
                DemoDetailSection(title="Открытые вопросы", kind="bullets", items=final_recommendation["open_questions"])
            ],
        ),
    ])
    return steps


def _build_final_recommendation(outputs: dict[str, dict[str, Any]]) -> DemoFinalRecommendation:
    final_recommendation = outputs["final_recommendation"]
    return DemoFinalRecommendation(
        recommendation=DemoRecommendationCode(final_recommendation["recommendation"]),
        label=final_recommendation["label"],
        rationale=final_recommendation["rationale"],
        key_requirements=final_recommendation["key_requirements"],
        open_questions=final_recommendation["open_questions"],
        risks=final_recommendation["risks"],
        economics=final_recommendation["economics"],
        manual_checks=final_recommendation["manual_checks"],
        trace=outputs["trace"]["overall_explanation"],
    )


def _build_report_markdown(metadata: dict[str, Any], outputs: dict[str, dict[str, Any]]) -> str:
    final_recommendation = outputs["final_recommendation"]
    quotes = outputs["quotes_comparison"]
    economics = outputs["economics"]
    preliminary_analysis = outputs["requirements"].get("preliminary_analysis", {})
    procurement_block = ""
    if metadata.get("procurement_source"):
        procurement = metadata.get("procurement", {})
        documentation = procurement.get("attachment_names") or [item.get("display_name", "") for item in metadata.get("files", [])]
        documentation_block = "\n".join(f"- {item}" for item in documentation) or "- Документация не получена."
        blocked_note = (
            "\nДокументация не получена. Анализ невозможен до ручной загрузки файлов.\n"
            if metadata.get("attachments_status") == "manual_upload_required" or not metadata.get("files")
            else ""
        )
        procurement_block = (
            "## Источник закупки\n"
            f"- Источник: {metadata.get('procurement_source')}\n"
            f"- Номер извещения: {metadata.get('notice_number') or metadata.get('procurement_id')}\n"
            f"- Заказчик: {metadata.get('customer_name')}\n"
            f"- Закон: {metadata.get('law') or procurement.get('category') or 'не указан'}\n"
            f"- НМЦК: {procurement.get('initial_price') or 'не указана'} {procurement.get('currency') or ''}\n"
            f"- Срок подачи: {metadata.get('deadline') or 'не указан'}\n"
            f"- Ссылка на источник: {metadata.get('procurement_url')}\n"
            f"- Статус скачивания: {metadata.get('attachments_status')}\n"
            f"- Ручная загрузка требовалась: {'да' if metadata.get('manual_upload_required') else 'нет'}\n"
            f"- Скачано/добавлено файлов: {metadata.get('downloaded_files_count', len(metadata.get('files', [])))}\n\n"
            "### Документация\n"
            f"{documentation_block}\n"
            f"{blocked_note}\n"
        )
    return (
        "# Отчёт по загруженному прогону тендерного агента\n\n"
        f"- Run ID: {metadata['run_id']}\n"
        f"- Закупка: {metadata['tender_title']}\n"
        f"- Категория: {metadata['tender_category']}\n"
        f"- Заказчик: {metadata['customer_name']}\n"
        f"- Статус: {metadata['status']}\n"
        f"- Режим анализа: {metadata['analysis_mode']}\n"
        f"- Код рекомендации: {final_recommendation['recommendation']}\n\n"
        + procurement_block
        + "## Краткий вывод\n"
        + "\n".join(f"- {item}" for item in final_recommendation["rationale"])
        + "\n\n## Предварительный анализ закупки\n"
        + (
            "\n".join(f"- {item}" for item in preliminary_analysis.get("overview", []))
            if preliminary_analysis.get("overview")
            else "- Пока не удалось извлечь структурированные выводы из ТЗ."
        )
        + "\n\n### Ключевые требования и ограничения\n"
        + (
            "\n".join(f"- {item}" for item in preliminary_analysis.get("compliance_highlights", []))
            if preliminary_analysis.get("compliance_highlights")
            else "- Требуется ручная валидация ключевых требований по исходным документам."
        )
        + "\n\n### Ключевые условия договора\n"
        + (
            "\n".join(f"- {item}" for item in preliminary_analysis.get("contract_highlights", []))
            if preliminary_analysis.get("contract_highlights")
            else "- Ключевые условия договора нужно проверить вручную."
        )
        + "\n\n## Извлечённые ТКП\n"
        + (
            "\n".join(
                f"- {item.get('supplier_name', 'Поставщик')}: сумма={item.get('total_amount', 'unknown')} {item.get('currency', '')}, позиций={item.get('items_count', 'unknown')}"
                for item in quotes.get("suppliers", [])
            )
            if quotes.get("suppliers")
            else "- ТКП не загружены или не распознаны."
        )
        + "\n\n## Экономика\n"
        + "\n".join(f"- {item['label']}: {item['value']}" for item in economics["metrics"])
        + "\n\n## Ручные проверки\n"
        + "\n".join(f"- {item}" for item in final_recommendation["manual_checks"])
        + "\n"
    )


def _render_report_html(metadata: dict[str, Any], outputs: dict[str, dict[str, Any]]) -> str:
    def list_html(items: list[str]) -> str:
        return "".join(f"<li>{html.escape(item)}</li>" for item in items)

    def is_missing(value: Any) -> bool:
        if value is None:
            return True
        text = str(value).strip()
        return not text or text.lower() in {"не указан", "none", "null", "n/a", "—"}

    def format_value(value: Any, *, fallback: str = "не указано") -> str:
        return fallback if is_missing(value) else str(value).strip()

    def format_price(amount: Any, currency: Any) -> str:
        if amount in (None, ""):
            return "не указана"
        if isinstance(amount, float):
            amount_text = f"{amount:,.2f}".replace(",", " ").replace(".", ",")
        else:
            amount_text = str(amount)
        currency_text = str(currency).strip() if currency else ""
        return f"{amount_text} {currency_text}".strip()

    def build_archive_button_html(run_id: str, archive_available: bool) -> str:
        if not archive_available:
            return ""
        return (
            f'<a class="action-button primary" href="/api/demo/tender-agent/runs/{html.escape(run_id)}/archive/download">Скачать архив</a>'
        )

    def build_document_list_html(run_id: str, files_payload: list[dict[str, Any]]) -> str:
        items: list[str] = []
        for item in files_payload:
            file_id = str(item.get("file_id") or "").strip()
            display_name = format_value(item.get("display_name"), fallback="Документ")
            if not file_id:
                continue
            items.append(
                f'<li><a class="doc-link" href="/api/demo/tender-agent/runs/{html.escape(run_id)}/files/{html.escape(file_id)}/download">{html.escape(display_name)}</a></li>'
            )
        if not items:
            return '<div class="muted">Документы для скачивания пока не доступны.</div>'
        return "".join(items)

    def build_document_toggle_html(run_id: str, files_payload: list[dict[str, Any]]) -> str:
        content = build_document_list_html(run_id, files_payload)
        if content.startswith("<div"):
            return content
        return (
            '<details class="document-toggle">'
            '<summary class="action-button">Показать документы</summary>'
            f'<ul class="document-list">{content}</ul>'
            '</details>'
        )

    def format_publication_update(publication_date: Any, updated_date: Any) -> str:
        publication = format_value(publication_date)
        updated = format_value(updated_date, fallback="")
        if updated and updated != publication:
            return f"{publication} / {updated}"
        return publication

    def render_table(columns: list[str], rows: list[dict[str, Any]]) -> str:
        if not rows:
            return "<p>Нет данных для отображения.</p>"
        header_html = "".join(f"<th>{html.escape(column)}</th>" for column in columns)
        body_html = "".join(
            "<tr>"
            + "".join(f"<td>{html.escape(str(row.get(column, '')))}</td>" for column in columns)
            + "</tr>"
            for row in rows
        )
        return f"<table><thead><tr>{header_html}</tr></thead><tbody>{body_html}</tbody></table>"

    requirements = outputs["requirements"]
    questions = outputs["supplier_questions"]
    quotes = outputs["quotes_comparison"]
    economics = outputs["economics"]
    risks = outputs["contract_risks"]
    final_recommendation = outputs["final_recommendation"]
    trace = outputs["trace"]
    preliminary_analysis = requirements.get("preliminary_analysis", {})
    files = metadata.get("files", [])
    procurement = metadata.get("procurement", {})
    procurement_manual_required = bool(metadata.get("manual_upload_required") or metadata.get("attachments_status") == "manual_upload_required" or not files)
    procurement_url = str(metadata.get("procurement_url") or procurement.get("source_url") or "").strip()
    notice_number = format_value(metadata.get("notice_number") or metadata.get("procurement_id") or procurement.get("procurement_number"))
    notice_number_html = (
        f'<a class="inline-link" href="{html.escape(procurement_url)}" target="_blank" rel="noopener noreferrer">{html.escape(notice_number)}</a>'
        if procurement_url and notice_number != "не указано"
        else html.escape(notice_number)
    )
    publication_update = format_publication_update(
        metadata.get("publication_date") or procurement.get("publication_date"),
        metadata.get("updated_date") or procurement.get("updated_date"),
    )
    downloaded_files_count = int(metadata.get("downloaded_files_count", len(files)))
    archive_available = (get_demo_run_input_dir(str(metadata.get("run_id"))) / "documentation-archive.zip").is_file()
    archive_button_html = build_archive_button_html(str(metadata.get("run_id")), archive_available)
    document_toggle_html = build_document_toggle_html(str(metadata.get("run_id")), files)

    return f"""
    <html lang="ru">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Отчёт по загруженному прогону тендерного агента</title>
        <style>
          body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: #001432;
            color: #ffffff;
          }}
          .page {{
            max-width: 1080px;
            margin: 0 auto;
            padding: 24px;
          }}
          .card {{
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(200,210,220,0.16);
            border-radius: 18px;
            padding: 20px;
            margin-bottom: 16px;
          }}
          h1, h2, h3 {{ margin-top: 0; }}
          .badge {{
            display: inline-block;
            padding: 8px 12px;
            border-radius: 999px;
            background: rgba(0,200,160,0.15);
            border: 1px solid rgba(120,250,230,0.25);
            margin-right: 8px;
            margin-bottom: 8px;
          }}
          table {{ width: 100%; border-collapse: collapse; }}
          th, td {{ text-align: left; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.1); }}
          th {{ color: #78FAE6; font-size: 12px; text-transform: uppercase; }}
          ul {{ margin: 0; padding-left: 18px; }}
          .muted {{ color: rgba(255,255,255,0.75); }}
          .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px 18px;
            margin-top: 18px;
          }}
          .metric {{
            padding: 12px 14px;
            border-radius: 14px;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
          }}
          .metric-label {{
            display: block;
            font-size: 12px;
            text-transform: uppercase;
            color: #78FAE6;
            margin-bottom: 6px;
          }}
          .metric-value {{
            display: block;
            font-size: 15px;
            line-height: 1.4;
          }}
          .downloads {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 16px;
            align-items: flex-start;
          }}
          .action-button {{
            display: inline-flex;
            align-items: center;
            padding: 10px 14px;
            border-radius: 999px;
            color: #ffffff;
            text-decoration: none;
            border: 1px solid rgba(120,250,230,0.3);
            background: rgba(255,255,255,0.05);
          }}
          .action-button.primary {{
            background: rgba(0,200,160,0.18);
          }}
          .inline-link {{
            color: #9cfbee;
            text-decoration: none;
            border-bottom: 1px dashed rgba(156,251,238,0.5);
          }}
          .document-toggle {{
            min-width: 240px;
          }}
          .document-toggle summary {{
            list-style: none;
          }}
          .document-toggle summary::-webkit-details-marker {{
            display: none;
          }}
          .document-list {{
            margin-top: 12px;
            padding-left: 18px;
          }}
          .document-list li + li {{
            margin-top: 8px;
          }}
          .doc-link {{
            color: #ffffff;
            text-decoration: none;
            border-bottom: 1px dashed rgba(255,255,255,0.35);
          }}
          .table-scroll {{
            overflow-x: auto;
            margin-top: 12px;
          }}
        </style>
      </head>
      <body>
        <div class="page">
          <div class="card">
            <div class="badge">Демо / пилотный режим</div>
            <div class="badge">Без внешних действий</div>
            <div class="badge">Требуется подтверждение человека</div>
            <h1>{html.escape(metadata['tender_title'])}</h1>
            <div class="summary-grid">
              <div class="metric"><span class="metric-label">Номер извещения</span><span class="metric-value">{notice_number_html}</span></div>
              <div class="metric"><span class="metric-label">Категория закупки</span><span class="metric-value">{html.escape(format_value(metadata.get('law') or metadata.get('tender_category') or procurement.get('category')))}</span></div>
              <div class="metric"><span class="metric-label">Заказчик</span><span class="metric-value">{html.escape(format_value(metadata.get('customer_name') or procurement.get('customer_name')))}</span></div>
              <div class="metric"><span class="metric-label">НМЦК</span><span class="metric-value">{html.escape(format_price(procurement.get('initial_price'), procurement.get('currency')))}</span></div>
              <div class="metric"><span class="metric-label">Дата публикации / обновления</span><span class="metric-value">{html.escape(publication_update)}</span></div>
              <div class="metric"><span class="metric-label">Срок подачи</span><span class="metric-value">{html.escape(format_value(metadata.get('deadline') or procurement.get('deadline')))}</span></div>
              <div class="metric"><span class="metric-label">Статус подключения</span><span class="metric-value">{html.escape("Документы получены через ЕИС" if metadata.get("procurement_source") else "Документы загружены вручную")}</span></div>
              <div class="metric"><span class="metric-label">Скачано документов</span><span class="metric-value">{downloaded_files_count}</span></div>
            </div>
            <div class="downloads">{archive_button_html}{document_toggle_html}</div>
            {('<p class="muted">Документация не получена. Анализ невозможен до ручной загрузки файлов.</p>' if procurement_manual_required and not files else '')}
          </div>

          <div class="card">
            <h2>Предварительный анализ закупки</h2>
            <ul>{list_html(preliminary_analysis.get('overview', [])) or "<li>Пока не удалось извлечь структурированные выводы из ТЗ.</li>"}</ul>
            {(
                '<h3>Спецификация ТЗ</h3><div class="table-scroll">'
                + render_table(
                    preliminary_analysis.get('spec_table', {}).get('columns', []),
                    preliminary_analysis.get('spec_table', {}).get('rows', []),
                )
                + '</div>'
            ) if preliminary_analysis.get('spec_table', {}).get('rows') else ''}
            <h3>Ключевые требования и ограничения</h3>
            <ul>{list_html(preliminary_analysis.get('compliance_highlights', [])) or "<li>Требуется ручная валидация ключевых требований по исходным документам.</li>"}</ul>
            <h3>Модель исполнения</h3>
            <ul>{list_html(preliminary_analysis.get('delivery_model', [])) or "<li>Формат исполнения нужно уточнить вручную.</li>"}</ul>
            <h3>Ключевые условия договора</h3>
            <ul>{list_html(preliminary_analysis.get('contract_highlights', [])) or "<li>Ключевые условия договора нужно проверить вручную.</li>"}</ul>
            <h3>Что делать дальше</h3>
            <ul>{list_html(preliminary_analysis.get('next_actions', []))}</ul>
          </div>

          <div class="card">
            <h2>Извлечённые требования</h2>
            <ul>{list_html([item['title'] for item in requirements['requirements']])}</ul>
          </div>

          <div class="card">
            <h2>Вопросы поставщикам</h2>
            <ul>{list_html(questions['questions'])}</ul>
          </div>

          <div class="card">
            <h2>RFQ draft</h2>
            <ul>{list_html(outputs['rfq_draft']['sections'])}</ul>
          </div>

          <div class="card">
            <h2>Извлечённые ТКП</h2>
            {render_table(
                ["Поставщик", "Файл", "Сумма", "Валюта", "Позиций", "Уверенность"],
                [
                    {
                        "Поставщик": item.get("supplier_name", "Поставщик"),
                        "Файл": item.get("source_file", "unknown"),
                        "Сумма": item.get("total_amount", "unknown"),
                        "Валюта": item.get("currency", "unknown"),
                        "Позиций": item.get("items_count", "unknown"),
                        "Уверенность": item.get("price_confidence", "unknown"),
                    }
                    for item in quotes.get("suppliers", [])
                ],
            )}
            <p class="muted">{html.escape(" ".join(quotes.get("limitations", [])))}</p>
          </div>

          <div class="card">
            <h2>Сравнение ТКП</h2>
            <ul>{list_html(quotes['highlights'])}</ul>
            {render_table(
                ["Позиция", "Лучшая цена", "Разброс %", "Нужна проверка"],
                [
                    {
                        "Позиция": item.get("normalized_name", "unknown"),
                        "Лучшая цена": item.get("best_price_supplier", "unknown"),
                        "Разброс %": item.get("price_spread_percent", "unknown"),
                        "Нужна проверка": "да" if item.get("needs_review") else "нет",
                    }
                    for item in quotes.get("items", [])[:24]
                ],
            )}
          </div>

          <div class="card">
            <h2>Экономика</h2>
            <ul>{list_html([f"{item['label']}: {item['value']}" for item in economics['metrics']])}</ul>
            <ul>{list_html(economics.get('manual_checks', []))}</ul>
            <p class="muted">{html.escape(" ".join(economics.get("limitations", [])))}</p>
          </div>

          <div class="card">
            <h2>Контрактные риски</h2>
            <ul>{list_html([item['risk'] for item in risks['risks']])}</ul>
          </div>

          <div class="card">
            <h2>Финальная рекомендация</h2>
            <p><strong>{html.escape(final_recommendation['label'])}</strong></p>
            <ul>{list_html(final_recommendation['rationale'])}</ul>
            <ul>{list_html(final_recommendation['manual_checks'])}</ul>
          </div>

          <div class="card">
            <h2>Трассировка и обоснование</h2>
            <p>{html.escape(trace['overall_explanation'])}</p>
            <ul>{list_html(trace.get('limitations', []))}</ul>
          </div>
        </div>
      </body>
    </html>
    """


def _normalize_report_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _is_missing_metadata_value(value: Any) -> bool:
    if value is None:
        return True
    text = _normalize_report_text(str(value))
    return not text or text.lower() in {"не указан", "none", "null", "n/a", "—"}


def _extract_customer_name_from_text(*texts: str | None) -> str | None:
    xml_patterns = (
        r"<(?:\w+:)?customerName>([^<]+)</(?:\w+:)?customerName>",
        r"<(?:\w+:)?fullName>([^<]+)</(?:\w+:)?fullName>",
    )
    text_patterns = (
        r"(?im)^\s*Заказчик(?:а|у|ом|е)?\s*[:\-]\s*([^\n]{4,200})",
        r"(?im)^\s*([А-ЯA-Z][^\n]{3,180})\s+в лице[^\n]+именуем[а-яё ]+«Заказчик»",
    )
    for raw_text in texts:
        if not raw_text:
            continue
        for pattern in xml_patterns:
            match = re.search(pattern, raw_text)
            if match:
                candidate = _normalize_report_text(html.unescape(match.group(1)))
                if candidate:
                    return candidate
        for pattern in text_patterns:
            match = re.search(pattern, raw_text)
            if match:
                candidate = _normalize_report_text(html.unescape(match.group(1) if match.groups() else match.group(0)))
                if candidate:
                    return candidate
    return None


def _extract_updated_date_from_text(*texts: str | None) -> str | None:
    for raw_text in texts:
        if not raw_text:
            continue
        match = re.search(r"<(?:\w+:)?directDT>(\d{4})-(\d{2})-(\d{2})T", raw_text)
        if match:
            return f"{match.group(3)}.{match.group(2)}.{match.group(1)}"
        match = re.search(r"(?im)обновлено\s*[:\-]?\s*(\d{2}\.\d{2}\.\d{4})", raw_text)
        if match:
            return match.group(1)
    return None


def _enrich_procurement_metadata_from_documents(
    metadata: dict[str, Any],
    *,
    combined_text: str | None = None,
    notice_text: str | None,
    technical_spec_text: str | None,
    contract_draft_text: str | None,
) -> dict[str, Any]:
    procurement = dict(metadata.get("procurement") or {})
    customer_candidate = _extract_customer_name_from_text(combined_text, notice_text, contract_draft_text, technical_spec_text)
    if customer_candidate:
        if metadata.get("mode") == "procurement_search_intake" or _is_missing_metadata_value(metadata.get("customer_name")):
            metadata["customer_name"] = customer_candidate
        if metadata.get("mode") == "procurement_search_intake" or _is_missing_metadata_value(procurement.get("customer_name")):
            procurement["customer_name"] = customer_candidate

    if _is_missing_metadata_value(metadata.get("updated_date")) and _is_missing_metadata_value(procurement.get("updated_date")):
        updated_date = _extract_updated_date_from_text(notice_text)
        if updated_date:
            metadata["updated_date"] = updated_date
            procurement["updated_date"] = updated_date

    if procurement:
        metadata["procurement"] = procurement
    return metadata


def _persist_outputs(run_id: str, metadata: dict[str, Any], outputs: dict[str, dict[str, Any]], steps: list[DemoStep]) -> None:
    output_dir = _output_dir(run_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in outputs.items():
        _write_json(output_dir / f"{name}.json", payload)

    report_html = _render_report_html(metadata, outputs)
    (output_dir / "report.html").write_text(report_html, encoding="utf-8")
    report_json = {
        "run_id": run_id,
        "report_title": "Отчёт по загруженному прогону тендерного агента",
        "generated_at": _safe_datetime(),
        "recommendation": outputs["final_recommendation"]["recommendation"],
        "recommendation_label": outputs["final_recommendation"]["label"],
        "executive_summary": outputs["final_recommendation"]["rationale"],
        "manual_checks": outputs["final_recommendation"]["manual_checks"],
        "sections": [
            {"title": step.title, "kind": "bullets", "items": step.findings}
            for step in steps
        ],
        "report_markdown": _build_report_markdown(metadata, outputs),
    }
    _write_json(output_dir / "report.json", report_json)
    _write_json(output_dir / "steps.json", {"steps": [item.model_dump(mode="json") for item in steps]})


def _render_procurement_blocked_report_html(metadata: dict[str, Any]) -> str:
    procurement = metadata.get("procurement", {})
    procurement_url = str(metadata.get("procurement_url") or procurement.get("source_url") or "").strip()
    notice_number = str(metadata.get("notice_number") or metadata.get("procurement_id") or procurement.get("procurement_number") or "не указано")
    notice_number_html = (
        f'<a class="inline-link" href="{html.escape(procurement_url)}" target="_blank" rel="noopener noreferrer">{html.escape(notice_number)}</a>'
        if procurement_url and notice_number.strip() and notice_number != "не указано"
        else html.escape(notice_number)
    )
    publication_date = str(metadata.get("publication_date") or procurement.get("publication_date") or "не указано")
    updated_date = str(metadata.get("updated_date") or procurement.get("updated_date") or "").strip()
    publication_update = f"{publication_date} / {updated_date}" if updated_date and updated_date != publication_date else publication_date
    return f"""
    <html lang="ru">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Источник закупки: документация требуется</title>
        <style>
          body {{ margin:0; font-family: Arial, sans-serif; background:#001432; color:#fff; }}
          .page {{ max-width:960px; margin:0 auto; padding:24px; }}
          .card {{ background:rgba(255,255,255,.06); border:1px solid rgba(200,210,220,.16); border-radius:18px; padding:20px; margin-bottom:16px; }}
          .badge {{ display:inline-block; padding:8px 12px; border-radius:999px; background:rgba(0,200,160,.15); border:1px solid rgba(120,250,230,.25); margin-right:8px; }}
          .warning {{ color:#78FAE6; font-weight:700; }}
          .summary-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px 18px; margin-top:18px; }}
          .metric {{ padding:12px 14px; border-radius:14px; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08); }}
          .metric-label {{ display:block; font-size:12px; text-transform:uppercase; color:#78FAE6; margin-bottom:6px; }}
          .metric-value {{ display:block; font-size:15px; line-height:1.4; }}
          .inline-link {{ color:#9cfbee; text-decoration:none; border-bottom:1px dashed rgba(156,251,238,.5); }}
        </style>
      </head>
      <body>
        <div class="page">
          <div class="card">
            <span class="badge">Демо / пилотный режим</span>
            <span class="badge">Без внешних действий</span>
            <span class="badge">Требуется подтверждение человека</span>
            <h1>{html.escape(str(metadata.get("tender_title") or "Закупка"))}</h1>
            <div class="summary-grid">
              <div class="metric"><span class="metric-label">Номер извещения</span><span class="metric-value">{notice_number_html}</span></div>
              <div class="metric"><span class="metric-label">Категория закупки</span><span class="metric-value">{html.escape(str(metadata.get("law") or procurement.get("category") or "не указана"))}</span></div>
              <div class="metric"><span class="metric-label">Заказчик</span><span class="metric-value">{html.escape(str(metadata.get("customer_name") or procurement.get("customer_name") or "не указан"))}</span></div>
              <div class="metric"><span class="metric-label">НМЦК</span><span class="metric-value">{html.escape(str(procurement.get("initial_price") or "не указана"))} {html.escape(str(procurement.get("currency") or ""))}</span></div>
              <div class="metric"><span class="metric-label">Дата публикации / обновления</span><span class="metric-value">{html.escape(publication_update)}</span></div>
              <div class="metric"><span class="metric-label">Срок подачи</span><span class="metric-value">{html.escape(str(metadata.get("deadline") or procurement.get("deadline") or "не указан"))}</span></div>
              <div class="metric"><span class="metric-label">Статус подключения</span><span class="metric-value">Документы получены через ЕИС</span></div>
              <div class="metric"><span class="metric-label">Скачано документов</span><span class="metric-value">{html.escape(str(metadata.get("downloaded_files_count", len(metadata.get("files", [])))))}</span></div>
            </div>
            <p class="warning">Документация не получена. Анализ невозможен до ручной загрузки файлов.</p>
          </div>
        </div>
      </body>
    </html>
    """


def _ensure_procurement_blocked_report_html(run_id: str) -> Path | None:
    path = _report_html_path(run_id)
    if path.is_file():
        return path
    metadata = _load_metadata(run_id)
    if metadata.get("mode") != "procurement_search_intake" or metadata.get("files"):
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_procurement_blocked_report_html(metadata), encoding="utf-8")
    return path


def analyze_uploaded_demo_run(run_id: str) -> TenderOperatorUploadedRunAnalyzeResponse:
    metadata = _load_metadata(run_id)
    if not metadata.get("files") and metadata.get("status") == TenderOperatorUploadedRunStatus.DOCS_REQUIRED.value:
        metadata["analysis_status"] = "blocked"
        _save_metadata(run_id, metadata)
        append_demo_run_event(
            run_id,
            "analysis_blocked",
            "Анализ остановлен: документация не получена автоматически, требуется ручная загрузка.",
            {"status": metadata.get("status")},
        )
        raise HTTPException(status_code=409, detail="Документация ещё не загружена. Добавьте файлы вручную и повторите анализ.")

    metadata["status"] = TenderOperatorUploadedRunStatus.ANALYZING.value
    metadata["analysis_mode"] = "analyzing"
    metadata["analysis_status"] = "analyzing"
    _save_metadata(run_id, metadata)
    append_demo_run_event(
        run_id,
        "analysis_started",
        "Запущен контролируемый анализ локального demo-run.",
        {"mode": metadata.get("mode"), "files": len(metadata.get("files", []))},
    )

    try:
        documents = _collect_documents(run_id, metadata)
        warnings = list(dict.fromkeys(metadata.get("warnings", []) + [warning for doc in documents for warning in doc.warnings]))

        notice_text = _collect_role_text(documents, "notice") or _collect_role_text(documents, "supporting") or metadata["tender_title"]
        technical_spec_text = _collect_role_text(documents, "technical_spec")
        contract_draft_text = _collect_role_text(documents, "contract_draft")
        combined_text = "\n\n".join(doc.text for doc in documents if doc.text)
        quote_paths = _collect_quote_paths(run_id, metadata)
        spreadsheet_sources = _collect_spreadsheet_sources(documents)
        economics_inputs = metadata.get("economics_inputs", {})
        metadata = _enrich_procurement_metadata_from_documents(
            metadata,
            combined_text=combined_text,
            notice_text=notice_text,
            technical_spec_text=technical_spec_text,
            contract_draft_text=contract_draft_text,
        )

        profile = get_supplier_profile()
        doc_relevance = score_procurement_document_text(text=combined_text or "", profile=profile)
        metadata["document_relevance"] = doc_relevance
        append_demo_run_event(
            run_id,
            "relevance_document_scoring_completed",
            f"Скоринг документов выполнен: найдено {len(doc_relevance.get('document_matched_terms', []))} совпадений.",
            {"document_score": doc_relevance.get("document_score")},
        )

        core_complete = bool(technical_spec_text and contract_draft_text and notice_text)
        if not technical_spec_text and combined_text:
            technical_spec_text = combined_text[:6000]
        if not contract_draft_text:
            warnings.append("Contract draft text was not fully extracted; contract risks are partially inferred.")

        provider_mode = "llm"
        llm_result = _try_run_llm_workflow(
            run_id=run_id,
            notice_text=notice_text,
            technical_spec_text=technical_spec_text,
            contract_draft_text=contract_draft_text,
            quote_paths=quote_paths,
            provider_mode=provider_mode,
        )
        if llm_result is not None:
            requirements = llm_result.get("requirements", {})
            calibrated_risks = llm_result.get("contract_risks", [])
            supplier_questions = llm_result.get("supplier_questions", [])
            rfq_draft = llm_result.get("rfq_draft", {})
            analysis_mode = llm_result.get("analysis_mode", "llm_tender_operator_provider")
            append_demo_run_event(
                run_id,
                "llm_analysis_completed",
                f"LLM-анализ выполнен через {llm_result.get('resolved_provider', 'llm')}.",
                {"analysis_mode": analysis_mode, "resolved_provider": llm_result.get("resolved_provider")},
            )
        else:
            pilot_runner = _import_runner_module()
            requirements = pilot_runner._run_stub_requirements_extraction(notice_text, technical_spec_text, contract_draft_text)
            calibrated_risks = pilot_runner._run_stub_calibrated_contract_risk(contract_draft_text or combined_text)
            supplier_questions = pilot_runner._run_stub_supplier_questions()
            rfq_draft = {}
            analysis_mode = "controlled_runner_adapter" if core_complete else "fallback_deterministic_adapter"
            append_demo_run_event(
                run_id,
                "stub_analysis_fallback",
                "LLM-анализ недоступен, используется детерминированный fallback.",
                {"core_complete": core_complete},
            )

        spreadsheet_comparison = build_quote_comparison(spreadsheet_sources, analysis_mode)
        if spreadsheet_comparison.supplier_quotes_found:
            tkp_comparison = _serialize_quote_comparison(spreadsheet_comparison)
            economics_summary = build_economics_summary(
                quote_comparison=spreadsheet_comparison,
                analysis_mode=analysis_mode,
                target_margin_percent=float(economics_inputs.get("target_margin_percent", DEFAULT_TARGET_MARGIN_PERCENT)),
                logistics_reserve_percent=float(economics_inputs.get("logistics_reserve_percent", DEFAULT_LOGISTICS_RESERVE_PERCENT)),
                risk_reserve_percent=float(economics_inputs.get("risk_reserve_percent", DEFAULT_RISK_RESERVE_PERCENT)),
                payment_delay_days=int(economics_inputs.get("payment_delay_days", DEFAULT_PAYMENT_DELAY_DAYS)),
            )
            economics = _serialize_economics_summary(economics_summary)
        else:
            tkp_comparison = None
            economics = None
        bid_decision = llm_result.get("bid_decision") if llm_result else None

        supplier_search_outcome = _run_supplier_internet_search(
            tender_title=metadata.get("tender_title", ""),
            notice_text=notice_text,
            technical_spec_text=technical_spec_text,
        )
        metadata["supplier_search"] = {
            "query": supplier_search_outcome.query_used,
            "total_found": supplier_search_outcome.total_found,
            "suppliers": [
                {"name": s.name, "site": s.site, "snippet": s.snippet[:200], "signals": s.relevance_signals}
                for s in supplier_search_outcome.suppliers
            ],
        }
        if supplier_search_outcome.error:
            append_demo_run_event(run_id, "supplier_search_warning", f"Поиск поставщиков недоступен: {supplier_search_outcome.error}", {})
        elif supplier_search_outcome.total_found:
            append_demo_run_event(
                run_id, "supplier_search_completed", f"Найдено {supplier_search_outcome.total_found} потенциальных поставщиков.",
                {"query": supplier_search_outcome.query_used, "count": supplier_search_outcome.total_found},
            )

        limitations = list(dict.fromkeys(metadata.get("limitations", [])))
        if not core_complete:
            limitations.append("Full runner integration was partially applied because the uploaded package did not produce all core extracted texts.")
        if not quote_paths and not spreadsheet_sources:
            limitations.append("TKP not uploaded. Supplier comparison and economics remain blocked or partial.")
        if spreadsheet_sources:
            limitations.append("Spreadsheet normalization uses deterministic heuristics and may require manual review for нестандартные таблицы.")
            if tkp_comparison:
                limitations.extend(tkp_comparison.get("limitations", []))
            if economics:
                limitations.extend(economics.get("limitations", []))
        elif any(item["extension"] in {".xlsx", ".xls"} for item in metadata.get("files", [])):
            limitations.append("Spreadsheet files were uploaded, but structured extraction could not start.")

        metadata["warnings"] = sorted(set(warnings))
        metadata["limitations"] = limitations
        metadata["analysis_mode"] = analysis_mode
        metadata["analysis_status"] = "completed"

        outputs = _build_output_payloads(
            metadata=metadata,
            documents=documents,
            analysis_mode=analysis_mode,
            requirements=requirements,
            calibrated_risks=calibrated_risks,
            supplier_questions=supplier_questions,
            tkp_comparison=tkp_comparison,
            economics=economics,
            bid_decision=bid_decision,
            core_complete=core_complete,
        )
        steps = _build_steps_from_outputs(metadata, outputs)
        final_recommendation = _build_final_recommendation(outputs)
        status = TenderOperatorUploadedRunStatus.COMPLETED if core_complete and tkp_comparison else TenderOperatorUploadedRunStatus.COMPLETED_WITH_WARNINGS
        if final_recommendation.recommendation == DemoRecommendationCode.MANUAL_REVIEW_REQUIRED:
            status = TenderOperatorUploadedRunStatus.NEEDS_REVIEW if not tkp_comparison else TenderOperatorUploadedRunStatus.COMPLETED_WITH_WARNINGS

        metadata["status"] = status.value
        _save_metadata(run_id, metadata)
        _persist_outputs(run_id, metadata, outputs, steps)
        append_demo_run_event(
            run_id,
            "analysis_completed",
            "Анализ завершён в контролируемом demo-контуре.",
            {"status": status.value, "analysis_mode": analysis_mode},
        )

        return TenderOperatorUploadedRunAnalyzeResponse(
            run_id=run_id,
            status=status,
            analysis_mode=analysis_mode,
            warnings=metadata["warnings"],
            limitations=metadata["limitations"],
            steps=steps,
            final_recommendation=final_recommendation,
        )
    except HTTPException:
        raise
    except Exception as exc:
        metadata["status"] = TenderOperatorUploadedRunStatus.FAILED.value
        metadata["analysis_mode"] = "failed"
        metadata["analysis_status"] = "failed"
        metadata["warnings"] = list(dict.fromkeys(metadata.get("warnings", []) + [f"Analysis failed safely: {exc}"]))
        metadata["limitations"] = list(dict.fromkeys(metadata.get("limitations", []) + ["Fallback report generation failed. Manual operator review required."]))
        _save_metadata(run_id, metadata)
        append_demo_run_event(
            run_id,
            "analysis_blocked",
            "Анализ завершился безопасной остановкой из-за внутренней ошибки.",
            {"error": str(exc)},
        )

        failed_outputs = {
            "final_recommendation": {
                "recommendation": DemoRecommendationCode.MANUAL_REVIEW_REQUIRED.value,
                "label": "нужна ручная проверка",
                "rationale": ["Анализ не завершился полностью и был остановлен в безопасном режиме."],
                "key_requirements": ["Проверка пакета документов вручную"],
                "open_questions": ["Нужно повторно проверить загруженные файлы и формат документов."],
                "risks": ["Автоматический анализ не завершён"],
                "economics": ["Недостаточно данных"],
                "manual_checks": ["Повторно просмотреть пакет документов вручную."],
            },
            "trace": {
                "overall_explanation": "Система не выполнила внешних действий и остановила анализ в безопасном режиме после внутренней ошибки.",
                "per_step": {step: "Анализ остановлен в safe mode." for step in ("documents", "requirements", "supplier_search", "questions", "rfq", "quotes", "economics", "risks", "decision")},
                "limitations": metadata["limitations"],
            },
        }
        final_recommendation = _build_final_recommendation(failed_outputs)
        steps = [
            DemoStep(
                key="documents",
                order=1,
                title="Документы",
                short_title="Документы",
                status=DemoStepStatus.NEEDS_REVIEW,
                description="Анализ остановлен до полного прохождения pipeline.",
                agent_action="Система сохранила локальные файлы, но не завершила разбор.",
                result_summary="Run остановлен в safe mode.",
                findings=metadata["warnings"],
                human_review=["Проверить формат и содержимое загруженных файлов вручную."],
                trace="Безопасная остановка без внешних действий.",
                result_sections=[],
            )
        ]
        return TenderOperatorUploadedRunAnalyzeResponse(
            run_id=run_id,
            status=TenderOperatorUploadedRunStatus.FAILED,
            analysis_mode="failed",
            warnings=metadata["warnings"],
            limitations=metadata["limitations"],
            steps=steps,
            final_recommendation=final_recommendation,
        )


def _report_json_path(run_id: str) -> Path:
    return _output_dir(run_id) / "report.json"


def _report_html_path(run_id: str) -> Path:
    return _output_dir(run_id) / "report.html"


def _load_report_json(run_id: str) -> dict[str, Any]:
    path = _report_json_path(run_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Report is not available yet")
    return _read_json(path)


def get_uploaded_demo_run(run_id: str) -> TenderOperatorUploadedRunResponse:
    metadata = _load_metadata(run_id)
    steps: list[DemoStep] = []
    final_recommendation: DemoFinalRecommendation | None = None
    quote_comparison = None
    economics_summary = None
    outputs_path = _output_dir(run_id)
    if (outputs_path / "final_recommendation.json").is_file() and (outputs_path / "trace.json").is_file():
        outputs = {
            "final_recommendation": _read_json(outputs_path / "final_recommendation.json"),
            "trace": _read_json(outputs_path / "trace.json"),
        }
        final_recommendation = _build_final_recommendation(outputs)
    if (outputs_path / "report.json").is_file():
        report_json = _load_report_json(run_id)
        steps = [
            DemoStep.model_validate(
                {
                    "key": f"section-{index}",
                    "order": index,
                    "title": section["title"],
                    "short_title": section["title"],
                    "status": DemoStepStatus.DONE,
                    "description": section["title"],
                    "agent_action": section["title"],
                    "result_summary": section["title"],
                    "findings": section.get("items", []),
                    "human_review": [],
                    "trace": "Saved report section.",
                    "result_sections": [],
                }
            )
            for index, section in enumerate(report_json.get("sections", []), start=1)
        ]
    stored_steps_path = outputs_path / "steps.json"
    if stored_steps_path.is_file():
        steps = [DemoStep.model_validate(item) for item in _read_json(stored_steps_path).get("steps", [])]
    quote_path = outputs_path / "quotes_comparison.json"
    economics_path = outputs_path / "economics.json"
    if quote_path.is_file():
        quote_comparison = _coerce_quote_comparison_payload(_read_json(quote_path))
    if economics_path.is_file():
        economics_summary = _coerce_economics_summary_payload(_read_json(economics_path))
    report_path = _report_html_path(run_id)
    if not report_path.is_file():
        report_path = _ensure_procurement_blocked_report_html(run_id)

    return TenderOperatorUploadedRunResponse(
        run_id=metadata["run_id"],
        created_at=datetime.fromisoformat(metadata["created_at"]),
        mode=metadata["mode"],
        tender_title=metadata["tender_title"],
        tender_category=metadata["tender_category"],
        customer_name=metadata["customer_name"],
        notes=metadata.get("notes"),
        status=TenderOperatorUploadedRunStatus(metadata["status"]),
        analysis_mode=metadata.get("analysis_mode", "not_started"),
        files=[TenderOperatorUploadedFile.model_validate(item) for item in metadata.get("files", [])],
        limitations=metadata.get("limitations", []),
        warnings=metadata.get("warnings", []),
        human_in_the_loop=metadata.get("human_in_the_loop", True),
        external_actions=metadata.get("external_actions", False),
        no_platform_submission=metadata.get("no_platform_submission", True),
        no_email_sending=metadata.get("no_email_sending", True),
        no_digital_signature=metadata.get("no_digital_signature", True),
        procurement_source=metadata.get("procurement_source"),
        procurement_id=metadata.get("procurement_id"),
        procurement_url=metadata.get("procurement_url"),
        procurement_query=metadata.get("procurement_query"),
        procurement_notice_number=metadata.get("notice_number"),
        procurement_law=metadata.get("law"),
        token_owner=metadata.get("token_owner"),
        soap_method=metadata.get("soap_method"),
        eis_ref_id=metadata.get("getdocs_ref_id"),
        archive_url_present=metadata.get("archive_url_present", False),
        archive_downloaded=metadata.get("archive_downloaded", False),
        archive_download_status=metadata.get("archive_download_status"),
        archive_download_attempts=metadata.get("archive_download_attempts", 0),
        archive_source_host=metadata.get("archive_source_host"),
        archive_source_path=metadata.get("archive_source_path"),
        documents_extracted_count=metadata.get("documents_extracted_count", 0),
        downloaded_files_count=metadata.get("downloaded_files_count", len(metadata.get("files", []))),
        manual_upload_required=metadata.get("manual_upload_required", False),
        attachments_status=metadata.get("attachments_status"),
        steps=steps,
        final_recommendation=final_recommendation,
        quote_comparison=quote_comparison,
        economics_summary=economics_summary,
        report_html_url=f"/demo/tender-agent/runs/{run_id}/report" if report_path and report_path.is_file() else None,
        report_download_url=f"/api/demo/tender-agent/runs/{run_id}/report/download" if report_path and report_path.is_file() else None,
        uploaded_files_note="Используются только локальные данные. Абсолютные server-path намеренно скрыты из интерфейса.",
        events=load_demo_run_events(run_id),
        document_relevance=metadata.get("document_relevance"),
    )


def get_uploaded_demo_run_steps(run_id: str) -> TenderOperatorUploadedRunStepsResponse:
    steps_path = _output_dir(run_id) / "steps.json"
    metadata = _load_metadata(run_id)
    if not steps_path.is_file():
        return TenderOperatorUploadedRunStepsResponse(
            run_id=run_id,
            status=TenderOperatorUploadedRunStatus(metadata["status"]),
            steps=[],
        )
    payload = _read_json(steps_path)
    return TenderOperatorUploadedRunStepsResponse(
        run_id=run_id,
        status=TenderOperatorUploadedRunStatus(metadata["status"]),
        steps=[DemoStep.model_validate(item) for item in payload.get("steps", [])],
    )


def save_uploaded_demo_steps(run_id: str, steps: list[DemoStep]) -> None:
    _write_json(_output_dir(run_id) / "steps.json", {"steps": [item.model_dump(mode="json") for item in steps]})


def get_uploaded_demo_report(run_id: str) -> TenderOperatorDemoReportResponse:
    payload = _load_report_json(run_id)
    return TenderOperatorDemoReportResponse.model_validate(payload)


def get_uploaded_demo_report_download(run_id: str) -> FileResponse:
    path = _ensure_procurement_blocked_report_html(run_id) or _report_html_path(run_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Report HTML is not available yet")
    return FileResponse(path, media_type="text/html; charset=utf-8", filename=f"{run_id}_report.html")


def get_uploaded_demo_report_html(run_id: str) -> str:
    path = _ensure_procurement_blocked_report_html(run_id) or _report_html_path(run_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Report HTML is not available yet")
    return path.read_text(encoding="utf-8")


def get_uploaded_demo_source_file_download(run_id: str, file_id: str) -> FileResponse:
    metadata = _load_metadata(run_id)
    descriptor = next((item for item in metadata.get("files", []) if item.get("file_id") == file_id), None)
    if descriptor is None:
        raise HTTPException(status_code=404, detail="Source file was not found")
    input_dir = get_demo_run_input_dir(run_id).resolve()
    target = (input_dir / str(descriptor.get("stored_name") or "")).resolve()
    if input_dir not in target.parents and target != input_dir:
        raise HTTPException(status_code=400, detail="Invalid stored file path")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Stored source file is not available")
    return FileResponse(
        target,
        media_type=str(descriptor.get("content_type") or "application/octet-stream"),
        filename=str(descriptor.get("original_name") or descriptor.get("display_name") or target.name),
    )


def get_uploaded_demo_archive_download(run_id: str) -> FileResponse:
    path = get_demo_run_input_dir(run_id) / "documentation-archive.zip"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Documentation archive is not available")
    return FileResponse(path, media_type="application/zip", filename="documentation-archive.zip")
