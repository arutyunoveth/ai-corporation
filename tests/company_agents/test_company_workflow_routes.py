from src.modules.workflow_runs.company_workflow_routes import (
    COMPANY_WORKFLOW_ROUTES,
    get_company_workflow_route,
    list_company_workflow_routes,
)


def test_company_workflow_routes_defined():
    routes = list_company_workflow_routes()
    assert len(routes) >= 4


def test_tender_bid_no_bid_route_exists():
    route = get_company_workflow_route("company_tender_bid_no_bid")
    assert route.owner == "A10"
    assert "A11" in route.supporting_agents
    assert "A20" in route.supporting_agents
    assert "A21" in route.supporting_agents
    assert route.execution_mode == "sequential_metadata_only"
    assert route.runtime_execution_allowed is False


def test_architecture_review_route_exists():
    route = get_company_workflow_route("company_architecture_review")
    assert route.owner == "A40"
    assert route.runtime_execution_allowed is False


def test_release_readiness_route_exists():
    route = get_company_workflow_route("company_release_readiness")
    assert route.owner == "A42"
    assert route.runtime_execution_allowed is False


def test_all_routes_have_runtime_execution_disabled():
    for route in list_company_workflow_routes():
        assert route.runtime_execution_allowed is False, (
            f"Route {route.route_id} has runtime_execution_allowed=True"
        )


def test_all_routes_are_sequential_metadata_only():
    for route in list_company_workflow_routes():
        assert route.execution_mode == "sequential_metadata_only", (
            f"Route {route.route_id} has unexpected execution_mode: {route.execution_mode}"
        )
