"""Company workflow route metadata for M-051 Workflow Orchestrator.

These are metadata/control definitions only. No runtime execution is opened.
Workflow routes define how company agents collaborate on specific workflows.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CompanyWorkflowRoute:
    route_id: str
    owner: str
    supporting_agents: list[str]
    final_artifact: str
    execution_mode: str
    runtime_execution_allowed: bool = False


COMPANY_WORKFLOW_ROUTES: dict[str, CompanyWorkflowRoute] = {
    "company_tender_bid_no_bid": CompanyWorkflowRoute(
        route_id="company_tender_bid_no_bid",
        owner="A10",
        supporting_agents=["A11", "A20", "A21", "A42"],
        final_artifact="CEO Decision Memo",
        execution_mode="sequential_metadata_only",
        runtime_execution_allowed=False,
    ),
    "company_architecture_review": CompanyWorkflowRoute(
        route_id="company_architecture_review",
        owner="A40",
        supporting_agents=["A42"],
        final_artifact="Architecture Decision Record",
        execution_mode="sequential_metadata_only",
        runtime_execution_allowed=False,
    ),
    "company_release_readiness": CompanyWorkflowRoute(
        route_id="company_release_readiness",
        owner="A42",
        supporting_agents=["A40"],
        final_artifact="QA Readiness Memo",
        execution_mode="sequential_metadata_only",
        runtime_execution_allowed=False,
    ),
    "company_marketing_asset_review": CompanyWorkflowRoute(
        route_id="company_marketing_asset_review",
        owner="A51",
        supporting_agents=["A52"],
        final_artifact="Marketing Asset Approval Memo",
        execution_mode="sequential_metadata_only",
        runtime_execution_allowed=False,
    ),
    "company_sales_lead_qualification": CompanyWorkflowRoute(
        route_id="company_sales_lead_qualification",
        owner="A50",
        supporting_agents=["A20", "A21"],
        final_artifact="Lead Qualification Memo",
        execution_mode="sequential_metadata_only",
        runtime_execution_allowed=False,
    ),
}


def get_company_workflow_route(route_id: str) -> CompanyWorkflowRoute:
    if route_id not in COMPANY_WORKFLOW_ROUTES:
        known = ", ".join(sorted(COMPANY_WORKFLOW_ROUTES.keys()))
        raise ValueError(f"Unknown company workflow route '{route_id}'. Known: {known}")
    return COMPANY_WORKFLOW_ROUTES[route_id]


def list_company_workflow_routes() -> list[CompanyWorkflowRoute]:
    return list(COMPANY_WORKFLOW_ROUTES.values())
