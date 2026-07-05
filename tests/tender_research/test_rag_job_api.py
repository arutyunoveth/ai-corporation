from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app
from src.tender_research.rag.job_schemas import TenderAnalysisJobRecord, TenderJobStep

client = TestClient(app)


def _job_record(*, job_id: str = "job-001", job_type: str = "prepare", status: str = "queued") -> TenderAnalysisJobRecord:
    now = datetime(2026, 7, 6, 1, 0, 0, tzinfo=timezone.utc)
    return TenderAnalysisJobRecord(
        id=job_id,
        job_type=job_type,
        registry_number="0323100010326000013",
        status=status,
        progress_percent=45 if status == "running" else 0,
        current_step="build_chunks" if status == "running" else "queued",
        steps=[
            TenderJobStep(
                name="build_chunks",
                title="Построение чанков",
                status="running" if status == "running" else "pending",
                progress_percent=45 if status == "running" else 0,
                message="Выполняется",
            )
        ],
        result={"status": "completed"} if status.startswith("completed") else None,
        warnings=[],
        errors=[],
        report_path="data/rag/reports/report.md" if job_type == "analyze" else None,
        analysis_run_id="run-001" if job_type == "analyze" else None,
        created_at=now,
        started_at=now if status != "queued" else None,
        finished_at=now if status.startswith("completed") else None,
        updated_at=now,
        duration_seconds=12.5 if status.startswith("completed") else None,
        source="api",
        request={"registry_number": "0323100010326000013"},
        analysis_mode="balanced",
        current_section_title="Условия контракта" if status == "running" else None,
        current_section_index=6 if status == "running" else None,
        total_sections=10 if status == "running" else None,
    )


class TestJobApi:
    def test_start_prepare_job_returns_queued_job(self) -> None:
        with patch("src.tender_research.api.create_job", return_value=_job_record()), patch(
            "src.tender_research.api.submit_prepare_job"
        ) as mock_submit:
            response = client.post(
                "/api/tender-research/jobs/prepare",
                json={"registry_number": "0323100010326000013"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-001"
        assert data["job_type"] == "prepare"
        assert data["status"] == "queued"
        assert data["status_url"].endswith("/api/tender-research/jobs/job-001")
        mock_submit.assert_called_once()

    def test_start_analyze_job_returns_queued_job(self) -> None:
        with patch("src.tender_research.api.create_job", return_value=_job_record(job_type="analyze")), patch(
            "src.tender_research.api.submit_analyze_job"
        ) as mock_submit:
            response = client.post(
                "/api/tender-research/jobs/analyze",
                json={"registry_number": "0323100010326000013", "use_llm": True, "save_report": True},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["job_type"] == "analyze"
        assert data["status"] == "queued"
        mock_submit.assert_called_once()

    def test_start_analyze_job_persists_full_request_payload(self) -> None:
        payload = {
            "registry_number": "0323100010326000013",
            "provider": "llama_cpp",
            "model": "Qwen3-Embedding-4B",
            "base_url": "http://127.0.0.1:8090/v1",
            "use_llm": True,
            "llm_base_url": "http://127.0.0.1:8088/v1",
            "llm_model": "/Users/master/models/Qwen2.5-14B-Instruct-Q4_K_M.gguf",
            "limit": 8,
            "save_report": True,
        }
        with patch("src.tender_research.api.create_job", return_value=_job_record(job_type="analyze")) as mock_create, patch(
            "src.tender_research.api.submit_analyze_job"
        ):
            response = client.post("/api/tender-research/jobs/analyze", json=payload)

        assert response.status_code == 200
        request_payload = mock_create.call_args.kwargs["request"]
        assert request_payload["registry_number"] == payload["registry_number"]
        assert request_payload["provider"] == payload["provider"]
        assert request_payload["analysis_mode"] == "balanced"
        assert request_payload["llm_timeout_seconds"] is None
        assert mock_create.call_args.kwargs["job_type"] == "analyze"
        assert mock_create.call_args.kwargs["registry_number"] == "0323100010326000013"

    def test_get_job_status_returns_payload(self) -> None:
        with patch("src.tender_research.api.get_job", return_value=_job_record(status="running", job_type="analyze")):
            response = client.get("/api/tender-research/jobs/job-001")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "job-001"
        assert data["status"] == "running"
        assert data["progress_percent"] == 45
        assert data["current_step"] == "build_chunks"
        assert data["current_section_title"] == "Условия контракта"
        assert data["steps"][0]["name"] == "build_chunks"
        assert "password" not in response.text.lower()

    def test_list_jobs_returns_items(self) -> None:
        with patch(
            "src.tender_research.api.list_jobs",
            return_value=([_job_record(job_id="job-001"), _job_record(job_id="job-002", job_type="analyze")], 2),
        ):
            response = client.get(
                "/api/tender-research/jobs",
                params={"registry_number": "0323100010326000013", "limit": 5},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["limit"] == 5
        assert len(data["items"]) == 2
        assert data["items"][1]["job_type"] == "analyze"

    def test_missing_job_returns_404(self) -> None:
        with patch("src.tender_research.api.get_job", return_value=None):
            response = client.get("/api/tender-research/jobs/job-missing")

        assert response.status_code == 404
        assert response.json()["detail"] == "Analysis job not found"
