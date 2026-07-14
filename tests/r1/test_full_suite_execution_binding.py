from pathlib import Path
from scripts.r1.full_suite_binding import build_execution_binding, commit_tree

def test_binding_resolves_commit_tree_and_clean_worktree():
    root=Path.cwd(); commit=__import__('subprocess').check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(); tree=__import__('subprocess').check_output(['git','rev-parse','HEAD^{tree}'],cwd=root,text=True).strip()
    b=build_execution_binding(cwd=root,tested_commit=commit,tested_tree=tree,expected_remote=commit,remote_ref='origin/codex/r1-b5-release-acceptance',runner=root/'scripts/r1/run_full_suite_sharded.py',verifier=root/'scripts/r1/verify_full_suite_aggregate.py')
    assert b['commit_object_tree_sha']==b['cat_file_tree_sha']==tree
    dirty = bool(__import__('subprocess').check_output(['git','status','--porcelain'],cwd=root,text=True).strip())
    assert b['status'] == ('invalid' if dirty else 'PASS')
    assert b['commit_object_tree_sha']==b['cat_file_tree_sha']==tree

def test_binding_rejects_wrong_tree():
    root=Path.cwd(); commit=__import__('subprocess').check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(); b=build_execution_binding(cwd=root,tested_commit=commit,tested_tree='0'*40,expected_remote=commit,remote_ref='origin/codex/r1-b5-release-acceptance',runner=root/'scripts/r1/run_full_suite_sharded.py',verifier=root/'scripts/r1/verify_full_suite_aggregate.py'); assert b['status']=='invalid'; assert 'commit_tree_matches' in b['reason_codes']
