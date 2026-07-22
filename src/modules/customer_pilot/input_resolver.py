"""Server-owned procurement documents for a customer analysis run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.tender_research.models import (
    ProcurementDocumentChunk,
    ProcurementTender,
    ProcurementTenderDocument,
)


@dataclass(frozen=True)
class CustomerRunInputs:
    registry_number: str
    documents: list[Any]
    source_document_ids: list[str]
    warnings: list[str]
    limitations: list[str]


def resolve_customer_run_inputs(
    session: Session, registry_number: str
) -> CustomerRunInputs:
    """Resolve persisted production-intake text; caller paths are never accepted."""
    tender = session.scalar(
        select(ProcurementTender)
        .where(
            (ProcurementTender.registry_number == registry_number)
            | (ProcurementTender.purchase_number == registry_number)
        )
        .order_by(ProcurementTender.updated_at.desc(), ProcurementTender.id.desc())
    )
    if not tender:
        raise HTTPException(
            409, "No persisted procurement intake is available for this registry number"
        )
    rows = session.scalars(
        select(ProcurementTenderDocument)
        .where(
            ProcurementTenderDocument.tender_id == tender.id,
            ProcurementTenderDocument.download_status.in_(
                ("downloaded", "completed", "ready")
            ),
        )
        .order_by(
            ProcurementTenderDocument.file_name.asc(),
            func.coalesce(ProcurementTenderDocument.document_identity_hash, "").asc(),
            func.coalesce(ProcurementTenderDocument.sha256, "").asc(),
            ProcurementTenderDocument.id.asc(),
        )
    ).all()
    from src.modules.procurement_analysis.frozen_types import AnalyzedDocument
    from src.modules.tender_operator_agent_demo.upload_service import _detect_role

    documents, identities = [], []
    for row in rows:
        chunks = session.scalars(
            select(ProcurementDocumentChunk)
            .where(ProcurementDocumentChunk.document_id == row.id)
            .order_by(
                ProcurementDocumentChunk.chunk_index.asc(),
                ProcurementDocumentChunk.id.asc(),
            )
        ).all()
        text = "\n\n".join(chunk.text for chunk in chunks if chunk.text)
        if not text:
            continue
        name = row.file_name
        documents.append(
            AnalyzedDocument(
                name,
                "." + name.rsplit(".", 1)[-1].lower() if "." in name else ".txt",
                _detect_role(name),
                text,
                True,
                [],
                "persisted_procurement_intake",
                row.id,
                None,
            )
        )
        identities.append(row.document_identity_hash or row.sha256 or row.id)
    if not documents:
        raise HTTPException(
            409, "Persisted procurement intake has no usable extracted documents"
        )
    return CustomerRunInputs(registry_number, documents, identities, [], [])
