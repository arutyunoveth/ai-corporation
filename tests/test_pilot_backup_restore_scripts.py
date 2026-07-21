from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_backup_script_has_real_dump_and_atomic_publish() -> None:
    text = (ROOT / "deploy/pilot/scripts/backup.sh").read_text(encoding="utf-8")
    assert "pg_dump" in text and "-Fc" in text and "pg_restore --list" in text
    assert "mktemp -d" in text and 'mv "$tmp" "$output"' in text
    assert "artifacts.tar.gz" in text and "SHA256SUMS" in text


def test_restore_script_rejects_staging_and_unsafe_archives() -> None:
    text = (ROOT / "deploy/pilot/scripts/restore.sh").read_text(encoding="utf-8")
    assert 'target" != "arvectum-r7-staging"' in text
    assert '"$port" != "18081"' in text
    assert "x.isdev()" in text and "x.issym()" in text
    assert "shasum -a 256 -c SHA256SUMS" in text
