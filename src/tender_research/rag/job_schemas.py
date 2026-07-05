from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel, Field


@dataclass
class TenderJobStep:
    name: str
    title: str
    status: str = "pending"
    progress_percent: int = 0
    message: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    details: str | dict | list | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "status": self.status,
            "progress_percent": self.progress_percent,
            "message": self.message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "details": self.details,
        }


@dataclass
class TenderAnalysisJobRecord:
    id: str
    job_type: str
    registry_number: str
    status: str
    progress_percent: int = 0
    current_step: str | None = None
    steps: list[TenderJobStep] = field(default_factory=list)
    result: dict | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    report_path: str | None = None
    analysis_run_id: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime | None = None
    duration_seconds: float | None = None
    source: str | None = None
    request: dict | None = None
    analysis_mode: str | None = None
    current_section_title: str | None = None
    current_section_index: int | None = None
    total_sections: int | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "job_type": self.job_type,
            "registry_number": self.registry_number,
            "status": self.status,
            "progress_percent": self.progress_percent,
            "current_step": self.current_step,
            "steps": [step.to_dict() for step in self.steps],
            "result": self.result,
            "warnings": self.warnings,
            "errors": self.errors,
            "report_path": self.report_path,
            "analysis_run_id": self.analysis_run_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "duration_seconds": self.duration_seconds,
            "source": self.source,
            "analysis_mode": self.analysis_mode,
            "current_section_title": self.current_section_title,
            "current_section_index": self.current_section_index,
            "total_sections": self.total_sections,
        }


class TenderJobStepSchema(BaseModel):
    name: str
    title: str
    status: str
    progress_percent: int = Field(default=0, ge=0, le=100)
    message: str = ""
    started_at: str | None = None
    finished_at: str | None = None
    details: dict | list | str | None = None


class StartJobResponse(BaseModel):
    job_id: str
    job_type: str
    registry_number: str
    status: str
    status_url: str


class JobStatusResponse(BaseModel):
    id: str
    job_type: str
    registry_number: str
    status: str
    progress_percent: int = Field(default=0, ge=0, le=100)
    current_step: str | None = None
    steps: list[TenderJobStepSchema] = Field(default_factory=list)
    result: dict | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    report_path: str | None = None
    analysis_run_id: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    updated_at: str | None = None
    duration_seconds: float | None = None
    source: str | None = None
    analysis_mode: str | None = None
    current_section_title: str | None = None
    current_section_index: int | None = None
    total_sections: int | None = None


class JobListResponse(BaseModel):
    items: list[JobStatusResponse]
    limit: int
    offset: int
    total: int
