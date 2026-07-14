from pathlib import Path
from scripts.r1.full_suite_binding import build_execution_binding, commit_tree
import subprocess

def test_binding_resolves_commit_tree_and_clean_worktree():
    root=Path.cwd(); commit=__import__('subprocess').check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(); tree=__import__('subprocess').check_output(['git','rev-parse','HEAD^{tree}'],cwd=root,text=True).strip()
    b=build_execution_binding(cwd=root,tested_commit=commit,tested_tree=tree,expected_remote=commit,remote_ref='origin/codex/r1-b5-release-acceptance',runner=root/'scripts/r1/run_full_suite_sharded.py',verifier=root/'scripts/r1/verify_full_suite_aggregate.py')
    assert b['commit_object_tree_sha']==b['cat_file_tree_sha']==tree
    dirty = bool(__import__('subprocess').check_output(['git','status','--porcelain'],cwd=root,text=True).strip())
    assert b['status'] == ('invalid' if dirty else 'PASS')
    assert b['commit_object_tree_sha']==b['cat_file_tree_sha']==tree

def test_binding_rejects_wrong_tree():
    root=Path.cwd(); commit=__import__('subprocess').check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(); b=build_execution_binding(cwd=root,tested_commit=commit,tested_tree='0'*40,expected_remote=commit,remote_ref='origin/codex/r1-b5-release-acceptance',runner=root/'scripts/r1/run_full_suite_sharded.py',verifier=root/'scripts/r1/verify_full_suite_aggregate.py'); assert b['status']=='invalid'; assert 'commit_tree_matches' in b['reason_codes']

def test_binding_real_temporary_git_repository(tmp_path):
    repo=tmp_path/'repo'; repo.mkdir()
    def g(*args): return subprocess.check_output(['git',*args],cwd=repo,text=True).strip()
    g('init'); g('config','user.email','test@example.invalid'); g('config','user.name','Test'); (repo/'tracked').write_text('ok')
    g('add','tracked'); g('commit','-m','initial'); commit=g('rev-parse','HEAD'); tree=g('rev-parse','HEAD^{tree}')
    remote=tmp_path/'remote.git'; subprocess.check_call(['git','init','--bare',str(remote)]); g('remote','add','origin',str(remote)); g('push','-u','origin','HEAD:refs/heads/test')
    (repo/'runner').write_text('runner'); (repo/'verifier').write_text('verifier')
    g('add','runner','verifier'); g('commit','-m','runner fixtures')
    commit=g('rev-parse','HEAD'); tree=g('rev-parse','HEAD^{tree}'); g('push','origin','HEAD:refs/heads/test')
    b=build_execution_binding(cwd=repo,tested_commit=commit,tested_tree=tree,expected_remote=commit,remote_ref='origin/test',runner=repo/'runner',verifier=repo/'verifier')
    assert b['status']=='PASS'
