from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from src.modules.hermes_agent.schemas import HermesAnalysisResponse, HermesFinalRecommendation, HermesQualityCheck
from src.shared.config.settings import get_settings

logger = logging.getLogger(__name__)

FALLBACK_ANALYSIS_REASON = "Hermes недоступен. Выполнен fallback-анализ без LLM."


class HermesClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.hermes_base_url.rstrip("/")
        self.timeout = settings.hermes_timeout_seconds
        self.enabled = settings.hermes_enabled

    def analyze_procurement(self, context: dict, relevant_memory: list[dict] | None = None) -> HermesAnalysisResponse:
        if not self._can_operate():
            return self._fallback_analysis(context)

        payload = {
            "context": context,
            "relevant_memory": relevant_memory or [],
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self.base_url}/api/hermes/analyze", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return HermesAnalysisResponse.model_validate(data)
        except httpx.TimeoutException:
            logger.warning("Hermes analyze timeout after %ss", self.timeout)
        except httpx.ConnectError:
            logger.warning("Hermes connection refused at %s", self.base_url)
        except httpx.HTTPStatusError as e:
            logger.warning("Hermes HTTP error: %s %s", e.response.status_code, e.response.text[:200])
        except Exception:
            logger.exception("Hermes analyze_procurement unexpected error")

        return self._fallback_analysis(context)

    def improve_analysis(
        self,
        context: dict,
        current_analysis: HermesAnalysisResponse,
        quality_checks: list[HermesQualityCheck],
    ) -> HermesAnalysisResponse:
        if not self._can_operate():
            return current_analysis

        payload = {
            "context": context,
            "current_analysis": current_analysis.model_dump(mode="json"),
            "quality_checks": [c.model_dump(mode="json") for c in quality_checks],
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self.base_url}/api/hermes/improve", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return HermesAnalysisResponse.model_validate(data)
        except Exception:
            logger.exception("Hermes improve_analysis failed, keeping current analysis")
            return current_analysis

    def reflect_on_feedback(self, feedback: dict) -> dict:
        if not self._can_operate():
            return {"reflection": "Hermes disabled", "applied": False}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self.base_url}/api/hermes/reflect", json={"feedback": feedback})
                resp.raise_for_status()
                return resp.json()
        except Exception:
            logger.exception("Hermes reflect_on_feedback failed")
            return {"reflection": "Hermes unavailable", "applied": False}

    def healthcheck(self) -> bool:
        if not self.enabled:
            return False
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False

    def _can_operate(self) -> bool:
        if not self.enabled:
            logger.info("Hermes disabled via HERMES_ENABLED=false")
            return False
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except httpx.ConnectError:
            logger.info("Hermes not reachable at %s", self.base_url)
            return False
        except httpx.TimeoutException:
            logger.info("Hermes healthcheck timeout at %s", self.base_url)
            return False
        except Exception:
            logger.exception("Hermes healthcheck error")
            return False

    def _fallback_analysis(self, context: dict) -> HermesAnalysisResponse:
        tender = context.get("tender", {})
        docs = context.get("documents", [])

        roles = list(set(context.get("document_roles", [])))
        has_spec = any(
            "specification" in (r or "").lower() or "technical_specification" in (r or "").lower()
            for r in roles
        )

        status = "needs_review" if has_spec else "ready"
        reasons = [FALLBACK_ANALYSIS_REASON]
        if has_spec:
            reasons.append("Обнаружена спецификация/ТЗ, требуется ручной анализ.")

        return HermesAnalysisResponse(
            tender_id=tender.get("id", ""),
            document_roles=roles,
            summary={
                "subject": tender.get("title", ""),
                "customer": tender.get("customer_name", ""),
                "nmck": str(tender.get("nmck_amount", "")),
            },
            missing_data=[
                {"field": "line_items", "reason": "Hermes недоступен", "suggested_source": "спецификация"},
                {"field": "delivery_address", "reason": "Hermes недоступен", "suggested_source": "проект контракта"},
            ],
            final_recommendation=HermesFinalRecommendation(
                status=status,
                reason="; ".join(reasons),
            ),
        )
