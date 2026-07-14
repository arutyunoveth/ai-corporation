import subprocess
from pathlib import Path

from scripts.r1.full_suite_binding import build_execution_binding


def _repo(tmp_path: Path):
    repo = tmp_path / "repo"; repo.mkdir()
    def g(*args): return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()
    g("init"); g("config", "user.email", "test@example.invalid"); g("config", "user.name", "Test")
    (repo / "tracked").write_text("ok"); (repo / "runner").write_text("runner"); (repo / "verifier").write_text("verifier")
    g("add", "."); g("commit", "-m", "initial")
    remote = tmp_path / "remote.git"; subprocess.check_call(["git", "init", "--bare", str(remote)])
    g("remote", "add", "origin", str(remote)); g("push", "-u", "origin", "HEAD:refs/heads/test")
    return repo, g


def test_binding_resolves_commit_tree_and_clean_worktree(tmp_path):
    repo, g = _repo(tmp_path); commit = g("rev-parse", "HEAD"); tree = g("rev-parse", "HEAD^{tree}")
    binding = build_execution_binding(cwd=repo, tested_commit=commit, tested_tree=tree, expected_remote=commit,
        remote_ref="origin/test", runner=repo / "runner", verifier=repo / "verifier")
    assert binding["status"] == "PASS"
    assert binding["commit_object_tree_sha"] == binding["cat_file_tree_sha"] == tree


def test_binding_rejects_wrong_tree(tmp_path):
    repo, g = _repo(tmp_path); commit = g("rev-parse", "HEAD")
    binding = build_execution_binding(cwd=repo, tested_commit=commit, tested_tree="0" * 40,
        expected_remote=commit, remote_ref="origin/test", runner=repo / "runner", verifier=repo / "verifier")
    assert binding["status"] == "invalid"
    assert "commit_tree_matches" in binding["reason_codes"]


def test_binding_real_temporary_git_repository(tmp_path):
    repo, g = _repo(tmp_path); commit = g("rev-parse", "HEAD"); tree = g("rev-parse", "HEAD^{tree}")
    binding = build_execution_binding(cwd=repo, tested_commit=commit, tested_tree=tree, expected_remote=commit,
        remote_ref="origin/test", runner=repo / "runner", verifier=repo / "verifier")
    assert binding["status"] == "PASS"
