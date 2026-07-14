"""Git/worktree binding primitives for sealed exact-suite evidence."""
from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path

def git(args, cwd: Path) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
def sha256_file(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def commit_tree(commit: str, cwd: Path) -> tuple[str,str]:
    rev=git(["rev-parse", f"{commit}^{{tree}}"],cwd); obj=git(["cat-file","-p",commit],cwd); tree=next((x.split()[1] for x in obj.splitlines() if x.startswith("tree ")),"")
    return rev, tree
def worktree_clean(cwd: Path) -> tuple[bool,list[str]]:
    lines=git(["status","--porcelain"],cwd).splitlines(); disallowed=[x for x in lines if not x.startswith("?? tmp/")]
    return not disallowed, disallowed
def build_execution_binding(*, cwd: Path, tested_commit: str, tested_tree: str, expected_remote: str, remote_ref: str, runner: Path, verifier: Path) -> dict:
    rev,cat=commit_tree(tested_commit,cwd); head=git(["rev-parse","HEAD"],cwd); head_tree=git(["rev-parse","HEAD^{tree}"],cwd); remote=git(["rev-parse",remote_ref],cwd); clean,changes=worktree_clean(cwd)
    checks={"local_head_matches":head==tested_commit,"remote_ref_matches":remote==expected_remote,"expected_remote_matches_tested_commit":expected_remote==tested_commit,"commit_tree_matches":rev==tested_tree,"head_tree_matches":head_tree==tested_tree,"cat_file_tree_matches":cat==tested_tree,"working_tree_clean":clean,"runner_present":runner.is_file(),"verifier_present":verifier.is_file()}
    return {"schema_version":"1.0","runtime_format_version":"3.0","repository_root":str(cwd),"repository_identity":git(["remote","get-url","origin"],cwd),"branch":git(["branch","--show-current"],cwd),"remote_ref":remote_ref,"tested_commit_sha":tested_commit,"tested_tree_sha":tested_tree,"expected_remote_sha":expected_remote,"observed_local_head_sha":head,"observed_head_tree_sha":head_tree,"observed_remote_sha":remote,"commit_object_tree_sha":rev,"cat_file_tree_sha":cat,"working_tree_clean":clean,"staged_changes":any(x.startswith(("A ","M ","D ","R ")) for x in changes),"unstaged_changes":bool(changes),"untracked_changes":[],"runner_path":str(runner),"runner_sha256":sha256_file(runner),"verifier_path":str(verifier),"verifier_sha256":sha256_file(verifier),"checks":checks,"reason_codes":[k for k,v in checks.items() if not v],"status":"PASS" if all(checks.values()) else "invalid"}
