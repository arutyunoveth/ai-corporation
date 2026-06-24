from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from openpyxl import Workbook

from src.modules.tender_operator_agent_demo.schemas import ProcurementSourceDescriptor
from src.modules.tender_operator_agent_demo.settings import get_zakupki_soap_settings


@dataclass(frozen=True)
class DemoProcurementAttachment:
    name: str
    content_type: str
    payload: bytes


@dataclass(frozen=True)
class DemoProcurementRecord:
    procurement_id: str
    source: str
    title: str
    procurement_number: str
    customer_name: str
    category: str
    publication_date: str
    deadline: str
    initial_price: float | None
    currency: str
    region: str
    source_url: str
    attachments_status: str
    summary: str
    source_note: str | None
    attachments: tuple[DemoProcurementAttachment, ...] = ()


def _quote_workbook_bytes(supplier_name: str, total_multiplier: float) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "ТКП"
    sheet.append(["№", "Наименование", "Кол-во", "Ед. изм.", "Цена", "Сумма", "Срок поставки", "Валюта"])
    sheet.append([1, "Шкаф управления", 2, "шт", round(120000 * total_multiplier, 2), round(240000 * total_multiplier, 2), "38 дней", "RUB"])
    sheet.append([2, "Кабель силовой", 100, "м", round(450 * total_multiplier, 2), round(45000 * total_multiplier, 2), "38 дней", "RUB"])
    sheet.append([3, f"Поставщик: {supplier_name}", None, None, None, None, None, None])
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def get_procurement_source_descriptors() -> list[ProcurementSourceDescriptor]:
    zakupki_status = get_zakupki_soap_settings().safe_status()
    return [
        ProcurementSourceDescriptor(
            code="demo_local",
            label="Демо-набор (локальный)",
            enabled=True,
            read_only=True,
            note="Офлайн-источник для стабильной демонстрации без сети.",
        ),
        ProcurementSourceDescriptor(
            code="public_eis_html_44fz",
            label="Публичный поиск ЕИС 44-ФЗ",
            enabled=True,
            read_only=True,
            note="Публичный fallback: открыть поиск ЕИС по 44-ФЗ, выбрать закупку и вставить реестровый номер в getDocsIP.",
        ),
        ProcurementSourceDescriptor(
            code="public_eis_html_223fz",
            label="Публичный поиск ЕИС 223-ФЗ (fallback)",
            enabled=True,
            read_only=True,
            note="Публичный fallback: открыть поиск ЕИС по 223-ФЗ и продолжить работу вручную. Отдельный parser не включён в этом спринте.",
        ),
        ProcurementSourceDescriptor(
            code="zakupki_gov_ru_getdocs_ip",
            label="zakupki_gov_ru_getdocs_ip",
            enabled=bool(zakupki_status["configured"]),
            read_only=True,
            note=zakupki_status["reason"] or "Токен физлица найден. getDocsIP доступен для read-only получения документации по номеру закупки.",
        ),
    ]


def get_demo_local_procurements() -> list[DemoProcurementRecord]:
    return [
        DemoProcurementRecord(
            procurement_id="DEMO-PR-001",
            source="demo_local",
            title="Поставка электротехнического оборудования для модернизации РУ-0,4 кВ",
            procurement_number="AO-2026-00117",
            customer_name="Промышленный заказчик",
            category="Электротехническое оборудование",
            publication_date="2026-06-14",
            deadline="2026-06-28",
            initial_price=12850000,
            currency="RUB",
            region="Москва",
            source_url="https://demo.local/procurements/DEMO-PR-001",
            attachments_status="downloadable",
            summary="Публичная демонстрационная закупка с комплектом документации и синтетическими ТКП.",
            source_note="Документация доступна в безопасном локальном demo-хранилище.",
            attachments=(
                DemoProcurementAttachment(
                    name="notice.txt",
                    content_type="text/plain",
                    payload=(
                        "Извещение о закупке.\n"
                        "Объект: поставка электротехнического оборудования.\n"
                        "Срок поставки: до 45 календарных дней.\n"
                        "Требуется приложить техническое описание и сертификаты.\n"
                    ).encode("utf-8"),
                ),
                DemoProcurementAttachment(
                    name="technical_spec.txt",
                    content_type="text/plain",
                    payload=(
                        "Техническое задание.\n"
                        "Позиции: шкафы управления, кабельная продукция, комплектующие.\n"
                        "Гарантия не менее 12 месяцев.\n"
                        "Подтверждение происхождения товара обязательно.\n"
                    ).encode("utf-8"),
                ),
                DemoProcurementAttachment(
                    name="contract_draft.txt",
                    content_type="text/plain",
                    payload=(
                        "Проект договора.\n"
                        "Штраф за просрочку поставки 0,1% в день.\n"
                        "Оплата после приёмки, отсрочка 45 дней.\n"
                    ).encode("utf-8"),
                ),
                DemoProcurementAttachment(
                    name="ТКП_ПоставщикА.xlsx",
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    payload=_quote_workbook_bytes("Поставщик А", 1.0),
                ),
                DemoProcurementAttachment(
                    name="ТКП_ПоставщикБ.xlsx",
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    payload=_quote_workbook_bytes("Поставщик Б", 0.96),
                ),
            ),
        ),
        DemoProcurementRecord(
            procurement_id="DEMO-PR-002",
            source="demo_local",
            title="Поставка кабельной продукции для производственного объекта",
            procurement_number="AO-2026-00123",
            customer_name="Промышленный заказчик",
            category="Кабельная продукция",
            publication_date="2026-06-16",
            deadline="2026-07-01",
            initial_price=7400000,
            currency="RUB",
            region="Санкт-Петербург",
            source_url="https://demo.local/procurements/DEMO-PR-002",
            attachments_status="downloadable",
            summary="Комплект документации доступен, но коммерческие предложения поставщиков ещё не загружены.",
            source_note="Анализ покажет RFQ и блокировку по ТКП до загрузки коммерческих предложений.",
            attachments=(
                DemoProcurementAttachment(
                    name="notice.txt",
                    content_type="text/plain",
                    payload=(
                        "Извещение о закупке по кабельной продукции.\n"
                        "Срок поставки: до 30 календарных дней.\n"
                    ).encode("utf-8"),
                ),
                DemoProcurementAttachment(
                    name="specification.txt",
                    content_type="text/plain",
                    payload=(
                        "Спецификация.\n"
                        "Кабель силовой ВВГнг, кабель контрольный, кабельные аксессуары.\n"
                        "Подтвердить сертификаты и техническое описание.\n"
                    ).encode("utf-8"),
                ),
                DemoProcurementAttachment(
                    name="contract_draft.txt",
                    content_type="text/plain",
                    payload=(
                        "Проект договора.\n"
                        "Оплата после поставки.\n"
                        "Штраф за просрочку и обязанность согласовать аналоги.\n"
                    ).encode("utf-8"),
                ),
            ),
        ),
        DemoProcurementRecord(
            procurement_id="DEMO-PR-003",
            source="demo_local",
            title="Поставка шкафов управления с монтажными комплектами",
            procurement_number="AO-2026-00135",
            customer_name="Промышленный заказчик",
            category="Шкафы управления",
            publication_date="2026-06-10",
            deadline="2026-06-25",
            initial_price=9800000,
            currency="RUB",
            region="Нижний Новгород",
            source_url="https://demo.local/procurements/DEMO-PR-003",
            attachments_status="manual_upload_required",
            summary="Публичная карточка доступна, но документация в demo-контуре не скачивается автоматически.",
            source_note="Для этой закупки нужно загрузить документы вручную.",
        ),
        DemoProcurementRecord(
            procurement_id="DEMO-PR-004",
            source="demo_local",
            title="Комплектующие для промышленной автоматизации",
            procurement_number="AO-2026-00141",
            customer_name="Промышленный заказчик",
            category="Промышленная автоматизация",
            publication_date="2026-06-18",
            deadline="2026-07-03",
            initial_price=5150000,
            currency="RUB",
            region="Екатеринбург",
            source_url="https://demo.local/procurements/DEMO-PR-004",
            attachments_status="downloadable",
            summary="Есть комплект документации, но часть позиций допускает аналоги и требует ручной проверки совместимости.",
            source_note="Подходит, чтобы показать honest needs_review по аналогам.",
            attachments=(
                DemoProcurementAttachment(
                    name="notice.txt",
                    content_type="text/plain",
                    payload=(
                        "Извещение.\n"
                        "Требуются контроллеры, датчики и комплектующие для автоматизации.\n"
                        "Допускаются аналоги при подтверждении совместимости.\n"
                    ).encode("utf-8"),
                ),
                DemoProcurementAttachment(
                    name="technical_spec.txt",
                    content_type="text/plain",
                    payload=(
                        "Техническое задание.\n"
                        "Срок поставки до 40 дней.\n"
                        "Гарантия 12 месяцев.\n"
                    ).encode("utf-8"),
                ),
                DemoProcurementAttachment(
                    name="contract_draft.txt",
                    content_type="text/plain",
                    payload=(
                        "Договор.\n"
                        "Требуется согласование аналогов до поставки.\n"
                        "Предусмотрены штрафы за нарушение сроков.\n"
                    ).encode("utf-8"),
                ),
            ),
        ),
        DemoProcurementRecord(
            procurement_id="DEMO-PR-005",
            source="demo_local",
            title="Поставка электротехнических материалов для резервного ремонта",
            procurement_number="AO-2026-00148",
            customer_name="Промышленный заказчик",
            category="Электротехническое оборудование",
            publication_date="2026-06-12",
            deadline="2026-06-30",
            initial_price=3100000,
            currency="RUB",
            region="Казань",
            source_url="https://demo.local/procurements/DEMO-PR-005",
            attachments_status="unavailable_in_demo",
            summary="Карточка закупки есть, но документация не подготовлена в синтетическом наборе.",
            source_note="Используйте ручную загрузку документов для продолжения.",
        ),
        DemoProcurementRecord(
            procurement_id="DEMO-PR-006",
            source="demo_local",
            title="Поставка комплектов КИПиА для производственной линии",
            procurement_number="AO-2026-00152",
            customer_name="Промышленный заказчик",
            category="Промышленная автоматизация",
            publication_date="2026-06-20",
            deadline="2026-07-05",
            initial_price=11200000,
            currency="RUB",
            region="Самара",
            source_url="https://demo.local/procurements/DEMO-PR-006",
            attachments_status="source_requires_authorization",
            summary="Источник в реальном мире потребовал бы авторизацию или интерактивный доступ, поэтому в demo включена ручная загрузка.",
            source_note="Этот кейс нужен для честного показа ограничений read-only контура.",
        ),
    ]
