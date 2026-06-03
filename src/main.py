from fastapi import FastAPI

from src.modules.compliance_matrix.router import router as compliance_matrix_router
from src.modules.deal_registry.router import router as deals_router
from src.modules.document_store.router import router as artifacts_router
from src.modules.document_ingestion.router import router as document_ingestion_router
from src.modules.document_requirements.router import router as document_requirements_router
from src.modules.event_log.router import router as event_log_router
from src.modules.initial_tech_risks.router import router as initial_tech_risks_router
from src.modules.priority_scoring.router import router as priority_scoring_router
from src.modules.status_engine.router import router as status_router
from src.modules.tender_screening.router import router as tender_screening_router
from src.modules.tender_intake.router import router as tender_intake_router
from src.modules.tender_summary.router import router as tender_summary_router
from src.shared.api.errors import register_exception_handlers
from src.shared.config.settings import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)
register_exception_handlers(app)

app.include_router(deals_router)
app.include_router(status_router)
app.include_router(artifacts_router)
app.include_router(event_log_router)
app.include_router(tender_intake_router)
app.include_router(document_ingestion_router)
app.include_router(tender_summary_router)
app.include_router(tender_screening_router)
app.include_router(priority_scoring_router)
app.include_router(compliance_matrix_router)
app.include_router(document_requirements_router)
app.include_router(initial_tech_risks_router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
