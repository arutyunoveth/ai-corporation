from __future__ import annotations

from src.tender_research.rag.job_service import (
    complete_job,
    create_job,
    fail_job,
    get_job,
    list_jobs,
    mark_job_running,
    update_job_progress,
)


def test_create_get_and_list_jobs(session):
    first = create_job(
        session,
        job_type="prepare",
        registry_number="0323100010326000013",
        request={"registry_number": "0323100010326000013"},
        source="api",
    )
    second = create_job(
        session,
        job_type="analyze",
        registry_number="0323100010326000014",
        request={"registry_number": "0323100010326000014", "use_llm": True},
        source="demo_ui",
    )

    fetched = get_job(session, first.id)
    items, total = list_jobs(session, limit=10, offset=0)
    filtered, filtered_total = list_jobs(session, registry_number="0323100010326000014", job_type="analyze")

    assert fetched is not None
    assert fetched.id == first.id
    assert fetched.status == "queued"
    assert fetched.request == {"registry_number": "0323100010326000013"}
    assert total == 2
    assert len(items) == 2
    assert filtered_total == 1
    assert filtered[0].id == second.id
    assert filtered[0].source == "demo_ui"


def test_mark_progress_and_complete_job(session):
    job = create_job(
        session,
        job_type="prepare",
        registry_number="0323100010326000013",
        request={"registry_number": "0323100010326000013"},
    )

    running = mark_job_running(session, job.id)
    progress = update_job_progress(
        session,
        job.id,
        progress_percent=55,
        current_step="extract_text",
        steps=[
            {
                "name": "extract_text",
                "title": "Извлечение текста",
                "status": "running",
                "progress_percent": 55,
                "message": "Обрабатываем документы",
            }
        ],
    )
    completed = complete_job(
        session,
        job.id,
        result={"ready_for_analysis": True, "status": "completed"},
        warnings=["1 document skipped"],
        status="completed_with_warnings",
        steps=[
            {
                "name": "completed",
                "title": "Завершение",
                "status": "completed",
                "progress_percent": 100,
                "message": "Готово",
            }
        ],
    )

    assert running is not None
    assert running.status == "running"
    assert running.started_at is not None
    assert progress is not None
    assert progress.progress_percent == 55
    assert progress.current_step == "extract_text"
    assert progress.steps[0].status == "running"
    assert completed is not None
    assert completed.status == "completed_with_warnings"
    assert completed.progress_percent == 100
    assert completed.warnings == ["1 document skipped"]
    assert completed.result == {"ready_for_analysis": True, "status": "completed"}
    assert completed.finished_at is not None
    assert completed.duration_seconds is not None


def test_fail_job_serializes_errors_and_filters_by_status(session):
    job = create_job(
        session,
        job_type="analyze",
        registry_number="0323100010326000013",
        request={"registry_number": "0323100010326000013", "use_llm": True},
    )

    mark_job_running(session, job.id)
    failed = fail_job(
        session,
        job.id,
        errors=["LLM unavailable"],
        warnings=["Fallback not configured"],
        current_step="section_analysis",
        steps=[
            {
                "name": "section_analysis",
                "title": "Анализ разделов",
                "status": "failed",
                "progress_percent": 60,
                "message": "Ошибка на шаге",
            }
        ],
    )
    failed_items, total = list_jobs(session, status="failed")

    assert failed is not None
    assert failed.status == "failed"
    assert failed.errors == ["LLM unavailable"]
    assert failed.warnings == ["Fallback not configured"]
    assert failed.current_step == "section_analysis"
    assert failed.steps[0].status == "failed"
    assert total == 1
    assert failed_items[0].id == job.id
