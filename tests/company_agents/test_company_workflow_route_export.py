"""Tests for company workflow route export."""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTE_SCRIPT = REPO_ROOT / "scripts" / "export_company_workflow_route.py"


def test_route_export_returns_valid_json():
    result = subprocess.run(
        [sys.executable, str(ROUTE_SCRIPT), "--route-id", "company_tender_bid_no_bid"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, f"Route export failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["route_id"] == "company_tender_bid_no_bid"


def test_route_export_has_required_fields():
    result = subprocess.run(
        [sys.executable, str(ROUTE_SCRIPT), "--route-id", "company_tender_bid_no_bid"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    data = json.loads(result.stdout)
    assert "route_id" in data
    assert "execution_mode" in data
    assert "runtime_execution_allowed" in data
    assert "owner" in data
    assert "supporting_agents" in data
    assert "final_artifact" in data
    assert "recommended_steps" in data


def test_route_export_runtime_execution_not_allowed():
    result = subprocess.run(
        [sys.executable, str(ROUTE_SCRIPT), "--route-id", "company_tender_bid_no_bid"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    data = json.loads(result.stdout)
    assert data["runtime_execution_allowed"] is False


def test_route_export_has_recommended_steps():
    result = subprocess.run(
        [sys.executable, str(ROUTE_SCRIPT), "--route-id", "company_tender_bid_no_bid"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    data = json.loads(result.stdout)
    assert len(data["recommended_steps"]) >= 4
    for step in data["recommended_steps"]:
        assert "step" in step
        assert "agent_id" in step
        assert "action" in step


def test_route_export_all_routes():
    route_ids = [
        "company_tender_bid_no_bid",
        "company_architecture_review",
        "company_release_readiness",
        "company_marketing_asset_review",
        "company_sales_lead_qualification",
    ]
    for route_id in route_ids:
        result = subprocess.run(
            [sys.executable, str(ROUTE_SCRIPT), "--route-id", route_id],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, f"Route export failed for {route_id}: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["route_id"] == route_id
        assert data["runtime_execution_allowed"] is False


def test_route_export_unknown_route_returns_error():
    result = subprocess.run(
        [sys.executable, str(ROUTE_SCRIPT), "--route-id", "nonexistent_route"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode != 0


def test_route_export_to_file(tmp_path):
    output_file = tmp_path / "route.json"
    result = subprocess.run(
        [sys.executable, str(ROUTE_SCRIPT), "--route-id", "company_tender_bid_no_bid", "--output", str(output_file)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0
    assert output_file.exists()
    data = json.loads(output_file.read_text())
    assert data["route_id"] == "company_tender_bid_no_bid"


def test_route_export_does_not_import_llm():
    result = subprocess.run(
        [sys.executable, str(ROUTE_SCRIPT), "--route-id", "company_tender_bid_no_bid"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert "openai" not in result.stderr.lower()
    assert "anthropic" not in result.stderr.lower()
    assert "llm" not in result.stderr.lower()
