"""Tests for company agent dry run 0 setup validation."""

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DRY_RUN_DIR = REPO_ROOT / "company_agent_runs" / "dry_run_0"


class TestDryRun0DirectoryStructure:
    """Verify dry run 0 directory structure exists."""

    def test_dry_run_dir_exists(self):
        assert DRY_RUN_DIR.is_dir()

    def test_input_dir_exists(self):
        assert (DRY_RUN_DIR / "input").is_dir()

    def test_exported_context_dir_exists(self):
        assert (DRY_RUN_DIR / "exported_context").is_dir()

    def test_artifacts_dir_exists(self):
        assert (DRY_RUN_DIR / "artifacts").is_dir()

    def test_final_dir_exists(self):
        assert (DRY_RUN_DIR / "final").is_dir()


class TestDryRun0Files:
    """Verify dry run 0 required files exist."""

    def test_readme_exists(self):
        readme = DRY_RUN_DIR / "README.md"
        assert readme.is_file()
        content = readme.read_text(encoding="utf-8")
        assert "Dry Run 0" in content
        assert "manual" in content.lower()

    def test_ceo_instruction_exists(self):
        instr = DRY_RUN_DIR / "input" / "ceo_instruction.md"
        assert instr.is_file()
        content = instr.read_text(encoding="utf-8")
        assert "CEO Instruction" in content
        assert "GO_TO_FIRST_PAID_RESTRICTED_PILOT" in content

    def test_run_manifest_template_exists(self):
        manifest_path = DRY_RUN_DIR / "run_manifest.template.json"
        assert manifest_path.is_file()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["run_id"] == "dry_run_0"
        assert manifest["runtime_execution_allowed"] is False
        assert manifest["llm_called_by_ai_corporation"] is False
        assert manifest["cloud_dispatch_allowed"] is False
        assert manifest["route_id"] == "company_pilot_readiness_review"


class TestTemplates:
    """Verify artifact templates exist."""

    TEMPLATES = [
        "A00_routing_memo.md",
        "A10_tender_operations_readiness.md",
        "A20_finance_readiness.md",
        "A21_legal_risk_readiness.md",
        "A42_qa_release_readiness.md",
        "A00_final_synthesis.md",
        "ceo_decision_memo.md",
    ]

    def test_templates_dir_exists(self):
        assert (REPO_ROOT / "docs" / "agents" / "company" / "templates").is_dir()

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_template_exists(self, template):
        path = REPO_ROOT / "docs" / "agents" / "company" / "templates" / template
        assert path.is_file(), f"Template {template} not found"


class TestRouteMetadata:
    """Verify company_pilot_readiness_review route exists and is safe."""

    def test_route_exists(self):
        from src.modules.workflow_runs.company_workflow_routes import (
            get_company_workflow_route,
        )

        route = get_company_workflow_route("company_pilot_readiness_review")
        assert route.route_id == "company_pilot_readiness_review"

    def test_route_runtime_execution_disabled(self):
        from src.modules.workflow_runs.company_workflow_routes import (
            get_company_workflow_route,
        )

        route = get_company_workflow_route("company_pilot_readiness_review")
        assert route.runtime_execution_allowed is False

    def test_route_owner_is_a00(self):
        from src.modules.workflow_runs.company_workflow_routes import (
            get_company_workflow_route,
        )

        route = get_company_workflow_route("company_pilot_readiness_review")
        assert route.owner == "A00"

    def test_route_supporting_agents(self):
        from src.modules.workflow_runs.company_workflow_routes import (
            get_company_workflow_route,
        )

        route = get_company_workflow_route("company_pilot_readiness_review")
        assert set(route.supporting_agents) == {"A10", "A20", "A21", "A42"}

    def test_route_final_artifact(self):
        from src.modules.workflow_runs.company_workflow_routes import (
            get_company_workflow_route,
        )

        route = get_company_workflow_route("company_pilot_readiness_review")
        assert route.final_artifact == "CEO Decision Memo"


class TestAgentContextExport:
    """Verify required agent contexts can be exported."""

    REQUIRED_AGENTS = ["A00", "A10", "A20", "A21", "A42"]

    @pytest.mark.parametrize("agent_id", REQUIRED_AGENTS)
    def test_agent_context_loads(self, agent_id):
        from scripts.export_company_agent_context import load_agent_context

        ctx = load_agent_context(agent_id)
        assert "identity" in ctx
        assert "soul" in ctx
        assert "agent" in ctx
        assert len(ctx["identity"]) > 0
        assert len(ctx["soul"]) > 0
        assert len(ctx["agent"]) > 0


class TestManifestSafety:
    """Verify manifest safety flags."""

    def test_manifest_execution_allowed_false(self):
        from scripts.export_hermes_company_manifest import build_manifest

        manifest = build_manifest()
        assert manifest["execution_allowed"] is False

    def test_manifest_autonomous_execution_allowed_false(self):
        from scripts.export_hermes_company_manifest import build_manifest

        manifest = build_manifest()
        assert manifest["autonomous_execution_allowed"] is False

    def test_manifest_cloud_dispatch_allowed_false(self):
        from scripts.export_hermes_company_manifest import build_manifest

        manifest = build_manifest()
        assert manifest["cloud_dispatch_allowed"] is False


class TestGitignoreProtection:
    """Verify .gitignore protects dry run outputs."""

    def test_gitignore_file_exists(self):
        gitignore = REPO_ROOT / ".gitignore"
        assert gitignore.is_file()

    def test_gitignore_blocks_exported_context(self):
        gitignore = REPO_ROOT / ".gitignore"
        content = gitignore.read_text(encoding="utf-8")
        assert "exported_context/*" in content

    def test_gitignore_blocks_artifacts(self):
        gitignore = REPO_ROOT / ".gitignore"
        content = gitignore.read_text(encoding="utf-8")
        assert "artifacts/*" in content

    def test_gitignore_blocks_final(self):
        gitignore = REPO_ROOT / ".gitignore"
        content = gitignore.read_text(encoding="utf-8")
        assert "final/*" in content

    def test_gitignore_allows_readme(self):
        gitignore = REPO_ROOT / ".gitignore"
        content = gitignore.read_text(encoding="utf-8")
        assert "!company_agent_runs/dry_run_0/README.md" in content

    def test_gitignore_allows_ceo_instruction(self):
        gitignore = REPO_ROOT / ".gitignore"
        content = gitignore.read_text(encoding="utf-8")
        assert "!company_agent_runs/dry_run_0/input/ceo_instruction.md" in content


class TestNoRealArtifactsCommitted:
    """Verify no real artifacts are committed."""

    def test_no_artifacts_in_artifacts_dir(self):
        artifacts_dir = DRY_RUN_DIR / "artifacts"
        files = [f for f in artifacts_dir.iterdir() if f.name != ".gitkeep"]
        assert len(files) == 0, f"Real artifacts found: {[f.name for f in files]}"

    def test_no_artifacts_in_final_dir(self):
        final_dir = DRY_RUN_DIR / "final"
        files = [f for f in final_dir.iterdir() if f.name != ".gitkeep"]
        assert len(files) == 0, f"Real artifacts found: {[f.name for f in files]}"

    def test_no_exported_context_committed(self):
        ctx_dir = DRY_RUN_DIR / "exported_context"
        files = [f for f in ctx_dir.iterdir() if f.name != ".gitkeep"]
        assert len(files) == 0, f"Real context found: {[f.name for f in files]}"
