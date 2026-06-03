from fastapi import FastAPI

from src.modules.bid_completeness.router import router as bid_completeness_router
from src.modules.bid_documents.router import router as bid_documents_router
from src.modules.bid_packages.router import router as bid_packages_router
from src.modules.cash_gap.router import router as cash_gap_router
from src.modules.ceo_approval.router import router as ceo_approval_router
from src.modules.compliance_matrix.router import router as compliance_matrix_router
from src.modules.contract_risks.router import router as contract_risks_router
from src.modules.cost_model.router import router as cost_model_router
from src.modules.deal_registry.router import router as deals_router
from src.modules.delivery_launch.router import router as delivery_launch_router
from src.modules.delivery_milestones.router import router as delivery_milestones_router
from src.modules.document_store.router import router as artifacts_router
from src.modules.document_ingestion.router import router as document_ingestion_router
from src.modules.document_requirements.router import router as document_requirements_router
from src.modules.event_log.router import router as event_log_router
from src.modules.execution_command.router import router as execution_command_router
from src.modules.finance_memo.router import router as finance_memo_router
from src.modules.financing_strategy.router import router as financing_strategy_router
from src.modules.initial_tech_risks.router import router as initial_tech_risks_router
from src.modules.integrated_risk_memo.router import router as integrated_risk_memo_router
from src.modules.priority_scoring.router import router as priority_scoring_router
from src.modules.post_submission.router import router as post_submission_router
from src.modules.outcome_intake.router import router as outcome_intake_router
from src.modules.payment_collection.router import router as payment_collection_router
from src.modules.quote_comparison.router import router as quote_comparison_router
from src.modules.quote_repository.router import router as quote_repository_router
from src.modules.rfq_generator.router import router as rfq_generator_router
from src.modules.shipping_acceptance.router import router as shipping_acceptance_router
from src.modules.status_engine.router import router as status_router
from src.modules.submission_readiness.router import router as submission_readiness_router
from src.modules.submission_control.router import router as submission_control_router
from src.modules.submission_receipts.router import router as submission_receipts_router
from src.modules.supplier_communications.router import router as supplier_communications_router
from src.modules.supplier_fulfillment.router import router as supplier_fulfillment_router
from src.modules.supplier_registry.router import router as supplier_registry_router
from src.modules.supplier_search.router import router as supplier_search_router
from src.modules.supplier_verification.router import router as supplier_verification_router
from src.modules.tender_screening.router import router as tender_screening_router
from src.modules.tender_intake.router import router as tender_intake_router
from src.modules.tender_summary.router import router as tender_summary_router
from src.shared.api.errors import register_exception_handlers
from src.shared.config.settings import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)
register_exception_handlers(app)

app.include_router(deals_router)
app.include_router(delivery_launch_router)
app.include_router(delivery_milestones_router)
app.include_router(status_router)
app.include_router(artifacts_router)
app.include_router(event_log_router)
app.include_router(execution_command_router)
app.include_router(tender_intake_router)
app.include_router(document_ingestion_router)
app.include_router(tender_summary_router)
app.include_router(tender_screening_router)
app.include_router(priority_scoring_router)
app.include_router(compliance_matrix_router)
app.include_router(document_requirements_router)
app.include_router(initial_tech_risks_router)
app.include_router(supplier_registry_router)
app.include_router(supplier_search_router)
app.include_router(rfq_generator_router)
app.include_router(supplier_communications_router)
app.include_router(quote_repository_router)
app.include_router(supplier_verification_router)
app.include_router(quote_comparison_router)
app.include_router(cost_model_router)
app.include_router(cash_gap_router)
app.include_router(financing_strategy_router)
app.include_router(finance_memo_router)
app.include_router(contract_risks_router)
app.include_router(integrated_risk_memo_router)
app.include_router(ceo_approval_router)
app.include_router(bid_documents_router)
app.include_router(bid_packages_router)
app.include_router(bid_completeness_router)
app.include_router(submission_readiness_router)
app.include_router(submission_control_router)
app.include_router(submission_receipts_router)
app.include_router(post_submission_router)
app.include_router(outcome_intake_router)
app.include_router(payment_collection_router)
app.include_router(shipping_acceptance_router)
app.include_router(supplier_fulfillment_router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
