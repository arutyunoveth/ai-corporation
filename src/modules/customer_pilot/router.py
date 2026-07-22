from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.modules.customer_pilot.models import (
    PilotAuditEvent,
    PilotFeedback,
    PilotProject,
    PilotReview,
    ProcurementCase,
)
from src.modules.customer_pilot.artifacts import verified_pdf_manifest
from src.modules.customer_registry.models import CustomerProfile
from src.shared.api.dependencies import DBSession
from src.shared.db.base import utcnow
from src.tender_research.models import TenderAnalysisRun

router = APIRouter(prefix="/api/operator/pilot", tags=["customer-pilot"])
CASE_STATUSES = {
    "created",
    "collecting_documents",
    "analyzing",
    "operator_review",
    "client_ready",
    "delivered",
    "archived",
    "failed",
}
TRANSITIONS = {
    "created": {"collecting_documents", "analyzing", "archived"},
    "collecting_documents": {"analyzing", "archived", "failed"},
    "analyzing": {"operator_review", "failed"},
    "operator_review": {"client_ready", "analyzing", "archived"},
    "client_ready": {"delivered", "archived"},
    "delivered": {"archived"},
    "failed": {"analyzing", "archived"},
    "archived": set(),
}
VERDICTS = {"approved", "approved_with_notes", "needs_reanalysis", "rejected"}
FEEDBACK_CATEGORIES = {
    "missing_requirement",
    "incorrect_requirement",
    "incorrect_risk",
    "source_mismatch",
    "report_usability",
    "supplier_relevance",
    "other",
}


class ProjectIn(BaseModel):
    name: str = Field(min_length=1)


class CaseIn(BaseModel):
    procurement_number: str | None = None


class StartIn(BaseModel):
    registry_number: str | None = None


class ReviewIn(BaseModel):
    reviewer: str
    verdict: str
    checklist: dict = Field(default_factory=dict)
    internal_comment: str | None = None
    client_comment: str | None = None
    source_graph_hash: str | None = None


class FeedbackIn(BaseModel):
    category: str
    severity: str
    expected_value: str | None = None
    observed_value: str | None = None
    comment: str | None = None


def _audit(
    session: Session,
    event: str,
    *,
    customer_id: str | None = None,
    project_id: str | None = None,
    case_id: str | None = None,
    run_id: str | None = None,
    payload: dict | None = None,
) -> None:
    # Deliberately retain only workflow metadata: never request headers/documents/secrets.
    session.add(
        PilotAuditEvent(
            customer_id=customer_id,
            project_id=project_id,
            procurement_case_id=case_id,
            run_id=run_id,
            event_type=event,
            payload=payload or {},
        )
    )


def _case(session: Session, customer_id: str, case_id: str) -> ProcurementCase:
    item = session.scalar(
        select(ProcurementCase).where(
            ProcurementCase.id == case_id, ProcurementCase.customer_id == customer_id
        )
    )
    if not item:
        raise HTTPException(404, "Procurement case not found")
    return item


def _run(
    session: Session, customer_id: str, case_id: str, run_id: str
) -> TenderAnalysisRun:
    item = session.scalar(
        select(TenderAnalysisRun).where(
            TenderAnalysisRun.id == run_id,
            TenderAnalysisRun.customer_id == customer_id,
            TenderAnalysisRun.procurement_case_id == case_id,
        )
    )
    if not item:
        raise HTTPException(404, "Analysis run not found")
    return item


def _transition(case: ProcurementCase, target: str) -> None:
    if target not in CASE_STATUSES or target not in TRANSITIONS.get(case.status, set()):
        raise HTTPException(
            409, f"Invalid lifecycle transition: {case.status} -> {target}"
        )
    case.status = target
    case.updated_at = utcnow()


@router.post("/customers/{customer_id}/projects", status_code=status.HTTP_201_CREATED)
def create_project(customer_id: str, payload: ProjectIn, session: DBSession):
    if not session.scalar(
        select(CustomerProfile).where(CustomerProfile.customer_id == customer_id)
    ):
        raise HTTPException(404, "Customer not found")
    slug = re.sub(r"[^a-z0-9]+", "-", payload.name.lower()).strip("-")[:48] or "project"
    project = PilotProject(
        customer_id=customer_id,
        name=payload.name.strip(),
        internal_slug=f"{slug}-{uuid4().hex[:10]}",
    )
    session.add(project)
    session.flush()
    _audit(session, "project_created", customer_id=customer_id, project_id=project.id)
    session.commit()
    return {
        "id": project.id,
        "customer_id": customer_id,
        "name": project.name,
        "internal_slug": project.internal_slug,
    }


@router.post(
    "/customers/{customer_id}/projects/{project_id}/cases",
    status_code=status.HTTP_201_CREATED,
)
def create_case(customer_id: str, project_id: str, payload: CaseIn, session: DBSession):
    if not session.scalar(
        select(PilotProject).where(
            PilotProject.id == project_id, PilotProject.customer_id == customer_id
        )
    ):
        raise HTTPException(404, "Project not found")
    case = ProcurementCase(
        customer_id=customer_id,
        project_id=project_id,
        procurement_number=payload.procurement_number,
        artifact_key=f"c_{uuid4().hex}",
    )
    session.add(case)
    session.flush()
    _audit(
        session,
        "case_created",
        customer_id=customer_id,
        project_id=project_id,
        case_id=case.id,
    )
    session.commit()
    return {
        "id": case.id,
        "customer_id": customer_id,
        "project_id": project_id,
        "status": case.status,
        "artifact_key": case.artifact_key,
    }


@router.post(
    "/customers/{customer_id}/cases/{case_id}/runs", status_code=status.HTTP_201_CREATED
)
def start_run(
    customer_id: str,
    case_id: str,
    payload: StartIn,
    session: DBSession,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    case = _case(session, customer_id, case_id)
    existing = session.scalar(
        select(TenderAnalysisRun).where(
            TenderAnalysisRun.procurement_case_id == case_id,
            TenderAnalysisRun.idempotency_key == idempotency_key,
        )
    )
    if existing:
        return {
            "id": existing.id,
            "status": existing.status,
            "idempotent": True,
            "artifact_key": existing.artifact_key,
        }
    startable = {"created", "collecting_documents", "failed", "operator_review"}
    claimed = session.execute(
        update(ProcurementCase)
        .where(
            ProcurementCase.id == case_id,
            ProcurementCase.customer_id == customer_id,
            ProcurementCase.status.in_(startable),
        )
        .values(status="analyzing", updated_at=utcnow())
    ).rowcount
    if claimed != 1:
        session.rollback()
        existing = session.scalar(
            select(TenderAnalysisRun).where(
                TenderAnalysisRun.procurement_case_id == case_id,
                TenderAnalysisRun.idempotency_key == idempotency_key,
            )
        )
        if existing:
            return {
                "id": existing.id,
                "status": existing.status,
                "idempotent": True,
                "artifact_key": existing.artifact_key,
            }
        raise HTTPException(409, "A run is already active or case cannot be started")
    run = TenderAnalysisRun(
        registry_number=payload.registry_number
        or case.procurement_number
        or "manual-documents",
        status="analyzing",
        customer_id=customer_id,
        project_id=case.project_id,
        procurement_case_id=case_id,
        idempotency_key=idempotency_key,
        artifact_key=f"r_{uuid4().hex}",
        source="customer_pilot",
    )
    try:
        session.add(run)
        session.flush()
    except IntegrityError:
        session.rollback()
        existing = session.scalar(
            select(TenderAnalysisRun).where(
                TenderAnalysisRun.procurement_case_id == case_id,
                TenderAnalysisRun.idempotency_key == idempotency_key,
            )
        )
        if existing:
            return {
                "id": existing.id,
                "status": existing.status,
                "idempotent": True,
                "artifact_key": existing.artifact_key,
            }
        raise HTTPException(409, "Concurrent analysis start was rejected")
    _audit(
        session,
        "analysis_started",
        customer_id=customer_id,
        project_id=case.project_id,
        case_id=case_id,
        run_id=run.id,
    )
    session.commit()
    return {
        "id": run.id,
        "status": run.status,
        "idempotent": False,
        "artifact_key": run.artifact_key,
    }


@router.post("/customers/{customer_id}/cases/{case_id}/runs/{run_id}/complete")
def complete_run(
    customer_id: str,
    case_id: str,
    run_id: str,
    session: DBSession,
    failed: bool = False,
):
    case = _case(session, customer_id, case_id)
    run = _run(session, customer_id, case_id, run_id)
    if run.status != "analyzing":
        raise HTTPException(409, "Run is not active")
    run.status = "failed" if failed else "completed"
    case.status = "failed" if failed else "operator_review"
    case.updated_at = utcnow()
    _audit(
        session,
        "analysis_failed" if failed else "analysis_completed",
        customer_id=customer_id,
        project_id=case.project_id,
        case_id=case_id,
        run_id=run_id,
    )
    session.commit()
    return {"id": run.id, "status": run.status, "case_status": case.status}


@router.post("/customers/{customer_id}/cases/{case_id}/runs/{run_id}/review")
def review_run(
    customer_id: str, case_id: str, run_id: str, payload: ReviewIn, session: DBSession
):
    case = _case(session, customer_id, case_id)
    run = _run(session, customer_id, case_id, run_id)
    if payload.verdict not in VERDICTS or case.status != "operator_review":
        raise HTTPException(409, "Review is not permitted")
    if session.scalar(select(PilotReview).where(PilotReview.run_id == run_id)):
        raise HTTPException(409, "Review is immutable; create a new run for re-review")
    manifest = (
        verified_pdf_manifest(run, case)
        if payload.verdict in {"approved", "approved_with_notes"}
        else {}
    )
    review = PilotReview(
        customer_id=customer_id,
        project_id=case.project_id,
        procurement_case_id=case_id,
        run_id=run_id,
        reviewer=payload.reviewer,
        verdict=payload.verdict,
        checklist=payload.checklist,
        internal_comment=payload.internal_comment,
        client_comment=payload.client_comment,
        source_graph_hash=payload.source_graph_hash,
        report_model_hash=manifest.get("report_model_hash"),
        artifact_hashes={"pdf": manifest.get("pdf_sha256"), "manifest": manifest},
        immutable_at=utcnow()
        if payload.verdict in {"approved", "approved_with_notes"}
        else None,
    )
    session.add(review)
    _audit(
        session,
        "review_updated",
        customer_id=customer_id,
        project_id=case.project_id,
        case_id=case_id,
        run_id=run_id,
        payload={"verdict": payload.verdict},
    )
    session.commit()
    return {
        "id": review.id,
        "verdict": review.verdict,
        "immutable": review.immutable_at is not None,
    }


@router.post("/customers/{customer_id}/cases/{case_id}/client-ready")
def mark_client_ready(customer_id: str, case_id: str, session: DBSession):
    case = _case(session, customer_id, case_id)
    approved = session.scalar(
        select(PilotReview).where(
            PilotReview.procurement_case_id == case_id,
            PilotReview.verdict.in_({"approved", "approved_with_notes"}),
        )
    )
    if not approved:
        raise HTTPException(409, "Completed approved operator review is required")
    run = _run(session, customer_id, case_id, approved.run_id)
    verified_pdf_manifest(run, case)
    _transition(case, "client_ready")
    _audit(
        session,
        "client_ready",
        customer_id=customer_id,
        project_id=case.project_id,
        case_id=case_id,
    )
    session.commit()
    return {"status": case.status}


@router.post("/customers/{customer_id}/cases/{case_id}/delivered")
def delivered(customer_id: str, case_id: str, session: DBSession):
    case = _case(session, customer_id, case_id)
    review = session.scalar(
        select(PilotReview).where(
            PilotReview.procurement_case_id == case_id,
            PilotReview.immutable_at.is_not(None),
        )
    )
    if not review or not review.artifact_hashes.get("pdf"):
        raise HTTPException(409, "Immutable final PDF is required")
    run = _run(session, customer_id, case_id, review.run_id)
    verified_pdf_manifest(run, case)
    _transition(case, "delivered")
    _audit(
        session,
        "delivered",
        customer_id=customer_id,
        project_id=case.project_id,
        case_id=case_id,
    )
    session.commit()
    return {"status": case.status}


@router.post("/customers/{customer_id}/cases/{case_id}/archive")
def archive_case(customer_id: str, case_id: str, session: DBSession):
    case = _case(session, customer_id, case_id)
    _transition(case, "archived")
    _audit(
        session,
        "case_archived",
        customer_id=customer_id,
        project_id=case.project_id,
        case_id=case_id,
    )
    session.commit()
    return {"status": case.status}


@router.post(
    "/customers/{customer_id}/cases/{case_id}/feedback",
    status_code=status.HTTP_201_CREATED,
)
def feedback(
    customer_id: str, case_id: str, run_id: str, payload: FeedbackIn, session: DBSession
):
    case = _case(session, customer_id, case_id)
    _run(session, customer_id, case_id, run_id)
    if payload.category not in FEEDBACK_CATEGORIES:
        raise HTTPException(422, "Unsupported feedback category")
    item = PilotFeedback(
        customer_id=customer_id,
        project_id=case.project_id,
        procurement_case_id=case_id,
        run_id=run_id,
        **payload.model_dump(),
    )
    session.add(item)
    _audit(
        session,
        "feedback_created",
        customer_id=customer_id,
        project_id=case.project_id,
        case_id=case_id,
        run_id=run_id,
    )
    session.commit()
    return {"id": item.id, "category": item.category}


@router.get("/customers/{customer_id}/cases/{case_id}/feedback")
def list_feedback(customer_id: str, case_id: str, session: DBSession):
    _case(session, customer_id, case_id)
    return [
        {
            "id": item.id,
            "run_id": item.run_id,
            "category": item.category,
            "severity": item.severity,
            "comment": item.comment,
            "created_at": item.created_at,
        }
        for item in session.scalars(
            select(PilotFeedback)
            .where(
                PilotFeedback.customer_id == customer_id,
                PilotFeedback.procurement_case_id == case_id,
            )
            .order_by(PilotFeedback.created_at.desc())
        )
    ]


@router.get("/customers/{customer_id}/cases/{case_id}")
def get_case(customer_id: str, case_id: str, session: DBSession):
    case = _case(session, customer_id, case_id)
    runs = session.scalars(
        select(TenderAnalysisRun).where(
            TenderAnalysisRun.customer_id == customer_id,
            TenderAnalysisRun.procurement_case_id == case_id,
        )
    ).all()
    return {
        "id": case.id,
        "customer_id": customer_id,
        "project_id": case.project_id,
        "status": case.status,
        "artifact_key": case.artifact_key,
        "runs": [
            {"id": r.id, "status": r.status, "artifact_key": r.artifact_key}
            for r in runs
        ],
    }


@router.get("/customers/{customer_id}/cases")
def list_cases(customer_id: str, session: DBSession):
    return [
        {
            "id": item.id,
            "project_id": item.project_id,
            "status": item.status,
            "procurement_number": item.procurement_number,
            "artifact_key": item.artifact_key,
        }
        for item in session.scalars(
            select(ProcurementCase)
            .where(ProcurementCase.customer_id == customer_id)
            .order_by(ProcurementCase.created_at.desc())
        )
    ]


@router.get("/summary")
def summary(session: DBSession):
    return {
        "active_runs": session.scalar(
            select(func.count())
            .select_from(TenderAnalysisRun)
            .where(TenderAnalysisRun.status == "analyzing")
        )
        or 0,
        "failed_runs": session.scalar(
            select(func.count())
            .select_from(TenderAnalysisRun)
            .where(TenderAnalysisRun.status == "failed")
        )
        or 0,
        "cases_awaiting_review": session.scalar(
            select(func.count())
            .select_from(ProcurementCase)
            .where(ProcurementCase.status == "operator_review")
        )
        or 0,
        "cases_ready_for_client": session.scalar(
            select(func.count())
            .select_from(ProcurementCase)
            .where(ProcurementCase.status == "client_ready")
        )
        or 0,
        "last_backup_at": None,
        "timestamp": datetime.now(UTC).isoformat(),
    }
