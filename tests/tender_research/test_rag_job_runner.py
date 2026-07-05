from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.tender_research.rag.job_runner import run_analyze_job, run_prepare_job
from src.tender_research.rag.prepare_service import TenderPreparationResult, TenderPreparationStep
from src.tender_research.rag.schemas import TenderAnalysisResult


def test_run_prepare_job_completes_and_persists_result() -> None:
    session = MagicMock()
    prepare_result = TenderPreparationResult(
        status="completed",
        registry_number="0323100010326000013",
        ready_for_analysis=True,
        steps=[TenderPreparationStep("readiness_check", "completed", "Ready")],
        tender_found=True,
        documents_total=4,
        documents_downloaded=4,
        extracted_texts_total=4,
        chunks_total=40,
        chunks_created=40,
        embeddings_total=40,
        embeddings_created=40,
    )

    def fake_prepare(*args, **kwargs):
        kwargs["progress_callback"](
            {
                "progress_percent": 100,
                "current_step": "readiness_check",
                "message": "Ready",
                "steps": prepare_result.steps,
            }
        )
        return prepare_result

    with patch("src.tender_research.rag.job_runner._get_session", return_value=session), patch(
        "src.tender_research.rag.job_runner.mark_job_running"
    ), patch(
        "src.tender_research.rag.job_runner.prepare_tender_for_analysis",
        side_effect=fake_prepare,
    ) as mock_prepare, patch(
        "src.tender_research.rag.job_runner.update_job_progress"
    ) as mock_progress, patch(
        "src.tender_research.rag.job_runner.complete_job"
    ) as mock_complete:
        run_prepare_job("job-prepare-1", {"registry_number": "0323100010326000013"})

    mock_prepare.assert_called_once()
    assert mock_progress.call_count >= 1
    mock_complete.assert_called_once()
    session.close.assert_called_once()


def test_run_analyze_job_completes_and_saves_history_link() -> None:
    session = MagicMock()
    analyze_result = TenderAnalysisResult(
        status="completed",
        registry_number="0323100010326000013",
        sections=[],
        sections_count=10,
        sources_count=30,
        report_markdown="# Preview",
        report_path="data/rag/reports/test.md",
        used_llm=True,
        run_id="run-123",
    )

    with patch("src.tender_research.rag.job_runner._get_session", return_value=session), patch(
        "src.tender_research.rag.job_runner.mark_job_running"
    ), patch(
        "src.tender_research.rag.job_runner.analyze_tender",
        return_value=analyze_result,
    ) as mock_analyze, patch(
        "src.tender_research.rag.job_runner.update_job_progress"
    ) as mock_progress, patch(
        "src.tender_research.rag.job_runner.complete_job"
    ) as mock_complete:
        run_analyze_job("job-analyze-1", {"registry_number": "0323100010326000013", "use_llm": True, "save_report": True})

    mock_analyze.assert_called_once()
    assert mock_progress.call_count >= 1
    mock_complete.assert_called_once()
    kwargs = mock_complete.call_args.kwargs
    assert kwargs["result"]["analysis_run_id"] == "run-123"
    assert kwargs["result"]["run_id"] == "run-123"
    assert kwargs["analysis_run_id"] == "run-123"
    assert kwargs["report_path"] == "data/rag/reports/test.md"
    session.close.assert_called_once()


def test_run_analyze_job_failure_marks_failed() -> None:
    session = MagicMock()

    with patch("src.tender_research.rag.job_runner._get_session", return_value=session), patch(
        "src.tender_research.rag.job_runner.mark_job_running"
    ), patch(
        "src.tender_research.rag.job_runner.analyze_tender",
        side_effect=RuntimeError("embedding server unavailable"),
    ), patch(
        "src.tender_research.rag.job_runner.update_job_progress"
    ), patch(
        "src.tender_research.rag.job_runner.fail_job"
    ) as mock_fail:
        run_analyze_job("job-analyze-2", {"registry_number": "0323100010326000013"})

    mock_fail.assert_called_once()
    assert "embedding server unavailable" in mock_fail.call_args.kwargs["errors"][0]
    session.close.assert_called_once()
