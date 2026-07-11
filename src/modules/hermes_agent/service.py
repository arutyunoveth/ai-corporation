from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.hermes_agent.client import HermesClient
from src.modules.hermes_agent.models import (
    AgentMemory,
    AnalysisQualityCheck as AnalysisQualityCheckModel,
    DocumentEvidenceSpan,
    TenderAnalysisFeedback,
    TenderEvalCase,
)
from src.modules.hermes_agent.category import (
    detect_procurement_category,
    list_available_categories,
    load_category_profile,
)
from src.modules.hermes_agent.nmck_mapping import extract_nmck_lines, map_line_items_to_nmck
from src.modules.hermes_agent.normalization import normalize_line_items
from src.modules.hermes_agent.quality import (
    determine_final_status,
    evidence_coverage_percentage,
    run_all_quality_gates,
    run_category_quality_gates,
)
from src.modules.hermes_agent.schemas import (
    HermesAnalysisResponse,
    HermesContextRequest,
    HermesDocumentContext,
    HermesFeedbackCreateRequest,
    HermesFinalRecommendation,
    HermesLineItem,
    HermesMemoryCreateRequest,
    HermesMemorySearchRequest,
    HermesQualityCheck,
    HermesRelevantMemory,
    HermesRuntimeAnalysisResult,
    HermesSummary,
    HermesTechnicalRequirement,
    HermesCertificationRequirement,
    HermesContractRisk,
    HermesMissingData,
    NmckMappingResult,
)
from src.modules.hermes_agent.supplier_readiness import build_supplier_readiness_memo

logger = logging.getLogger(__name__)


class HermesProcurementAnalysisService:
    def __init__(self, session: Session):
        self.session = session

    def build_context(self, tender_id: str) -> dict:
        from src.tender_research.models import ProcurementTenderDocument
        from src.tender_research.repository import TenderRepository
        repo = TenderRepository(self.session)
        tender = repo.get_tender_by_id(tender_id)
        if not tender:
            raise ValueError(f"Tender {tender_id} not found")

        documents = self.session.query(ProcurementTenderDocument).filter(
            ProcurementTenderDocument.tender_id == tender_id
        ).all()

        context = {
            "tender": {
                "id": tender.id,
                "registry_number": tender.registry_number,
                "title": tender.title,
                "customer_name": tender.customer_name,
                "customer_inn": tender.customer_inn,
                "nmck_amount": tender.nmck_amount,
                "law_type": tender.law_type,
                "publication_date": str(tender.publication_date) if tender.publication_date else None,
                "application_deadline": str(tender.application_deadline) if tender.application_deadline else None,
                "status": tender.status,
            },
            "documents": [],
            "document_roles": [],
        }

        for doc in documents:
            doc_info = {
                "id": doc.id,
                "file_name": doc.file_name,
                "content_type": doc.content_type,
                "download_status": doc.download_status,
                "text_extraction_status": doc.text_extraction_status,
                "size_bytes": doc.size_bytes,
                "extracted_text_chars": doc.extracted_text_chars,
                "role": self._infer_document_role(doc.file_name),
            }
            context["documents"].append(doc_info)
            if doc_info["role"]:
                context["document_roles"].append(doc_info["role"])

        context["document_roles"] = list(set(context["document_roles"]))
        return context

    def get_document_text(self, document_id: str) -> str:
        from src.tender_research.models import ProcurementTenderDocument
        doc = self.session.get(ProcurementTenderDocument, document_id)
        if not doc:
            raise ValueError(f"Document {document_id} not found")
        if doc.extracted_text_path:
            try:
                with open(doc.extracted_text_path, "r", encoding="utf-8") as f:
                    return f.read()
            except FileNotFoundError:
                pass
        chunks = list(doc.chunks)
        if chunks:
            chunks.sort(key=lambda c: c.chunk_index)
            return "\n".join(c.text for c in chunks)
        return ""

    def get_document_tables(self, document_id: str) -> list[dict]:
        from src.tender_research.models import ProcurementTenderDocument, ProcurementDocumentChunk
        doc = self.session.get(ProcurementTenderDocument, document_id)
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        tables: list[dict] = []
        chunks: list[ProcurementDocumentChunk] = list(doc.chunks)
        for chunk in chunks:
            if chunk.raw_meta and "table" in str(chunk.raw_meta.get("type", "")).lower():
                tables.append({
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "meta": chunk.raw_meta,
                })
            lines = chunk.text.split("\n")
            table_candidates = [l for l in lines if l.count("|") >= 2 or l.count("\t") >= 2]
            if table_candidates and len(table_candidates) >= 2:
                tables.append({
                    "chunk_index": chunk.chunk_index,
                    "lines": table_candidates[:50],
                    "source": "heuristic",
                })
        return tables

    def run_analysis(self, analysis: HermesAnalysisResponse) -> HermesAnalysisResponse:
        quality_checks = run_all_quality_gates(analysis)
        analysis.quality_checks = quality_checks

        status, reason = determine_final_status(analysis, quality_checks)
        analysis.final_recommendation = HermesFinalRecommendation(status=status, reason=reason)

        return analysis

    def validate_analysis_quality(self, analysis: HermesAnalysisResponse) -> list[HermesQualityCheck]:
        return run_all_quality_gates(analysis)

    def persist_analysis_with_evidence(
        self, tender_id: str, analysis: HermesAnalysisResponse
    ) -> str:
        analysis_id = str(import_uuid4())

        for check in analysis.quality_checks:
            qc = AnalysisQualityCheckModel(
                tender_id=tender_id,
                analysis_id=analysis_id,
                check_name=check.check_name,
                status=check.status,
                message=check.message,
            )
            self.session.add(qc)

        for item in analysis.line_items:
            if item.source_document and item.source_quote:
                span = DocumentEvidenceSpan(
                    tender_id=tender_id,
                    document_ref=item.source_document,
                    field_path=f"line_items.{item.position_no or item.name}",
                    quote=item.source_quote,
                    start_offset=0,
                    end_offset=0,
                    confidence=item.confidence,
                )
                self.session.add(span)

        for tr in analysis.technical_requirements:
            if tr.source_document and tr.source_quote:
                span = DocumentEvidenceSpan(
                    tender_id=tender_id,
                    document_ref=tr.source_document,
                    field_path="technical_requirements",
                    quote=tr.source_quote,
                    start_offset=0,
                    end_offset=0,
                    confidence=tr.confidence,
                )
                self.session.add(span)

        self.session.commit()
        return analysis_id

    def save_feedback_as_memory(self, feedback: HermesFeedbackCreateRequest) -> TenderAnalysisFeedback:
        fb = TenderAnalysisFeedback(
            tender_id=feedback.tender_id,
            analysis_id=feedback.analysis_id,
            field_path=feedback.field_path,
            feedback_type=feedback.feedback_type,
            user_comment=feedback.user_comment,
            corrected_value_json=feedback.corrected_value_json,
        )
        self.session.add(fb)
        self.session.flush()

        memory_payload = {
            "feedback_id": fb.id,
            "field_path": feedback.field_path,
            "feedback_type": feedback.feedback_type,
            "corrected_value": feedback.corrected_value_json,
            "user_comment": feedback.user_comment,
        }
        memory = AgentMemory(
            memory_type="feedback_error_case",
            scope="procurement_analysis",
            category=f"field_path:{feedback.field_path}",
            payload_json=memory_payload,
            source_tender_id=feedback.tender_id,
            source_analysis_id=feedback.analysis_id,
        )
        self.session.add(memory)
        self.session.commit()
        return fb

    def create_eval_case_from_feedback(
        self, tender_id: str, feedback: TenderAnalysisFeedback
    ) -> TenderEvalCase:
        must_not = {}
        if feedback.field_path:
            must_not[feedback.field_path] = True

        eval_case = TenderEvalCase(
            tender_id=tender_id,
            fixture_name=f"from_feedback_{feedback.id[:8]}",
            must_not_include_json=must_not if must_not else None,
        )
        self.session.add(eval_case)
        self.session.commit()
        return eval_case

    def search_memory(self, request: HermesMemorySearchRequest) -> list[AgentMemory]:
        query = select(AgentMemory)

        if request.memory_type:
            query = query.where(AgentMemory.memory_type == request.memory_type)
        if request.scope:
            query = query.where(AgentMemory.scope == request.scope)
        if request.category:
            query = query.where(AgentMemory.category == request.category)
        if request.source_tender_id:
            query = query.where(AgentMemory.source_tender_id == request.source_tender_id)

        query = query.order_by(AgentMemory.created_at.desc()).limit(request.limit)
        result = self.session.execute(query)
        return list(result.scalars().all())

    def create_memory(self, request: HermesMemoryCreateRequest) -> AgentMemory:
        memory = AgentMemory(
            memory_type=request.memory_type,
            scope=request.scope,
            category=request.category,
            payload_json=request.payload_json,
            source_tender_id=request.source_tender_id,
        )
        self.session.add(memory)
        self.session.commit()
        return memory

    def build_runtime_context(self, tender_id: str) -> dict:
        ctx = self.build_context(tender_id)
        for doc in ctx.get("documents", []):
            doc_id = doc.get("id", "")
            doc["text"] = self.get_document_text(doc_id)
            doc["tables"] = self.get_document_tables(doc_id)
        return ctx

    def load_relevant_memory(self, context: dict) -> list[dict]:
        memories: list[dict] = []
        tender_id = context.get("tender", {}).get("id", "")

        feedback_memories = self.search_memory(HermesMemorySearchRequest(
            memory_type="feedback_error_case",
            scope="procurement_analysis",
            limit=10,
        ))
        for m in feedback_memories:
            memories.append({
                "id": m.id,
                "memory_type": m.memory_type,
                "scope": m.scope,
                "category": m.category,
                "payload_json": m.payload_json,
            })

        rule_memories = self.search_memory(HermesMemorySearchRequest(
            memory_type="extraction_rule",
            scope="procurement_analysis",
            limit=10,
        ))
        for m in rule_memories:
            memories.append({
                "id": m.id,
                "memory_type": m.memory_type,
                "scope": m.scope,
                "category": m.category,
                "payload_json": m.payload_json,
            })

        if tender_id:
            tender_memories = self.search_memory(HermesMemorySearchRequest(
                source_tender_id=tender_id,
                limit=10,
            ))
            for m in tender_memories:
                memories.append({
                    "id": m.id,
                    "memory_type": m.memory_type,
                    "scope": m.scope,
                    "category": m.category,
                    "payload_json": m.payload_json,
                })
        return memories

    def run_runtime_analysis(self, tender_id: str) -> HermesRuntimeAnalysisResult:
        start_time = time.time()

        context = self.build_runtime_context(tender_id)
        documents = context.get("documents", [])
        document_roles = context.get("document_roles", [])

        relevant_memory = self.load_relevant_memory(context)
        applied_memory_count = len(relevant_memory)

        line_item_names_from_context: list[str] = []
        for memory in relevant_memory:
            payload = memory.get("payload_json", {}) if isinstance(memory, dict) else getattr(memory, "payload_json", {})
            if isinstance(payload, dict) and "line_items" in payload:
                for li in payload["line_items"]:
                    if isinstance(li, dict) and li.get("name"):
                        line_item_names_from_context.append(li["name"])

        client = HermesClient()
        analysis = client.analyze_procurement(context, relevant_memory)

        analysis.tender_id = tender_id
        analysis.document_roles = document_roles
        if not analysis.summary.subject and context.get("tender", {}).get("title"):
            analysis.summary.subject = context["tender"]["title"]

        line_item_names = [li.name for li in analysis.line_items]
        category = detect_procurement_category(context, line_item_names + line_item_names_from_context)
        profile = load_category_profile(category)
        category_label = (profile or {}).get("label", "") if profile else ""

        normalized_items = normalize_line_items(analysis.line_items, profile)

        nmck_docs = [d for d in documents if "nmck" in (d.get("role") or "").lower() or "расчет" in (d.get("role") or "").lower()]
        nmck_lines = extract_nmck_lines(nmck_docs if nmck_docs else documents)
        nmck_mapping = map_line_items_to_nmck(analysis.line_items, normalized_items, nmck_lines, profile)

        quality_checks = run_all_quality_gates(analysis)
        category_checks = run_category_quality_gates(
            analysis, category,
            normalized_items=normalized_items,
            nmck_mapping=nmck_mapping,
        )
        quality_checks.extend(category_checks)
        analysis.quality_checks = quality_checks

        failed_checks = [c for c in quality_checks if c.status == "failed"]
        improvement_attempted = False
        improvement_succeeded = False

        if failed_checks:
            improvement_attempted = True
            improvement_context = dict(context)
            improvement_context["category"] = category
            improvement_context["category_profile"] = profile
            improvement_context["category_checks_failed"] = [c.check_name for c in category_checks if c.status == "failed"]
            improvement_context["nmck_mapping_status"] = nmck_mapping.mapping_status

            improved = client.improve_analysis(improvement_context, analysis, quality_checks)
            if improved:
                improved.tender_id = tender_id
                improved.document_roles = document_roles
                improved_checks = run_all_quality_gates(improved)
                improved_category_checks = run_category_quality_gates(
                    improved, category,
                    normalized_items=normalize_line_items(improved.line_items, profile),
                    nmck_mapping=nmck_mapping,
                )
                improved.quality_checks = improved_checks + improved_category_checks
                improved_failed = [c for c in improved.quality_checks if c.status == "failed"]
                if len(improved_failed) < len(failed_checks) or improved.line_items:
                    improvement_succeeded = True
                    analysis = improved
                    quality_checks = improved.quality_checks
                    normalized_items = normalize_line_items(analysis.line_items, profile)

        status, reason = determine_final_status(analysis, quality_checks)
        analysis.final_recommendation = HermesFinalRecommendation(status=status, reason=reason)
        analysis.quality_checks = quality_checks

        docs_used = set()
        for item in analysis.line_items:
            if item.source_document:
                docs_used.add(item.source_document)
        for tr in analysis.technical_requirements:
            if tr.source_document:
                docs_used.add(tr.source_document)

        ev_pct = evidence_coverage_percentage(analysis)
        duration_ms = round((time.time() - start_time) * 1000, 1)

        intermediate_result = HermesRuntimeAnalysisResult(
            **analysis.model_dump(mode="json"),
            applied_memory_count=applied_memory_count,
            improvement_attempted=improvement_attempted,
            improvement_succeeded=improvement_succeeded,
            evidence_coverage_pct=ev_pct,
            documents_used_count=len(docs_used),
            documents_total_count=len(documents),
            procurement_category=category,
            category_label=category_label,
            normalized_line_items=normalized_items,
            nmck_mapping=nmck_mapping,
        )
        object.__setattr__(intermediate_result, "analysis_duration_ms", duration_ms)

        supplier_readiness_memo = build_supplier_readiness_memo(intermediate_result)
        object.__setattr__(intermediate_result, "supplier_readiness_memo", supplier_readiness_memo)

        self.persist_analysis_with_evidence(tender_id, analysis)

        return intermediate_result

    def run_self_improvement_if_needed(
        self,
        tender_id: str,
        analysis: HermesAnalysisResponse,
        quality_checks: list[HermesQualityCheck],
    ) -> HermesAnalysisResponse:
        failed = [c for c in quality_checks if c.status == "failed"]
        if not failed:
            return analysis

        context = self.build_runtime_context(tender_id)
        client = HermesClient()
        improved = client.improve_analysis(context, analysis, quality_checks)
        if improved:
            improved.tender_id = tender_id
        return improved or analysis

    def run_feedback_reflection(self, feedback_id: str) -> dict:
        fb = self.session.get(TenderAnalysisFeedback, feedback_id)
        if not fb:
            raise ValueError(f"Feedback {feedback_id} not found")

        client = HermesClient()
        reflection = client.reflect_on_feedback({
            "feedback_id": fb.id,
            "tender_id": fb.tender_id,
            "field_path": fb.field_path,
            "feedback_type": fb.feedback_type,
            "user_comment": fb.user_comment,
            "corrected_value": fb.corrected_value_json,
        })
        return reflection

    def _infer_document_role(self, file_name: str) -> str:
        name_lower = file_name.lower()
        if "извещение" in name_lower or "notice" in name_lower:
            return "notice"
        if "спецификация" in name_lower or "specification" in name_lower:
            return "specification"
        if "техническое задание" in name_lower or "тз" in name_lower or "technical_specification" in name_lower or "tech_spec" in name_lower:
            return "technical_specification"
        if "нмцк" in name_lower or "nmck" in name_lower or "расчет" in name_lower:
            return "nmck_calculation"
        if "контракт" in name_lower or "contract" in name_lower or "проект" in name_lower:
            return "draft_contract"
        if "приложение" in name_lower or "appendix" in name_lower:
            return "appendix"
        if "инструкция" in name_lower or "instruction" in name_lower:
            return "instruction"
        if "разъяснение" in name_lower or "clarification" in name_lower:
            return "clarification"
        if "обоснование" in name_lower or "justification" in name_lower:
            return "justification"
        return ""


def import_uuid4() -> str:
    from uuid import uuid4
    return str(uuid4())
