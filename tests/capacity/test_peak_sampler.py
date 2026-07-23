import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CAP_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "capacity" / "calibration"


class TestPeakSampler:
    def test_symlink_root_rejection(self):
        from scripts.capacity.calibration.peak_sampler import _real_path
        with tempfile.TemporaryDirectory() as td:
            real_dir = os.path.join(td, "real")
            link_dir = os.path.join(td, "link")
            os.mkdir(real_dir)
            os.symlink(real_dir, link_dir)
            try:
                _real_path(link_dir)
                assert False, "Should reject symlink root"
            except ValueError:
                pass
            resolved = _real_path(real_dir)
            assert os.path.isdir(resolved)

    def test_interval_validation(self):
        result = subprocess.run(
            [sys.executable, str(CAP_SCRIPTS / "peak_sampler.py"),
             "--root", "test=/tmp", "--interval-seconds", "1",
             "--output", "/dev/null"],
            capture_output=True, text=True
        )
        assert result.returncode != 0

    def test_requires_root(self):
        with tempfile.NamedTemporaryFile(suffix=".json") as f:
            result = subprocess.run(
                [sys.executable, str(CAP_SCRIPTS / "peak_sampler.py"),
                 "--interval-seconds", "2", "--output", f.name],
                capture_output=True, text=True
            )
            assert result.returncode != 0

    def test_no_absolute_paths_in_output(self):
        with tempfile.TemporaryDirectory() as td:
            out_path = os.path.join(td, "peak.json")
            subprocess.run(
                [sys.executable, str(CAP_SCRIPTS / "peak_sampler.py"),
                 "--root", f"test={td}", "--interval-seconds", "2",
                 "--oneshot", "--output", out_path],
                capture_output=True, timeout=10
            )
            data = json.loads(open(out_path).read())
            text = json.dumps(data)
            # Should not contain absolute paths (baseline.path is sanitized to root name)
            # The sanitizer replaces paths with root name, but /private/var may leak
            # through baseline.path on macOS. We check that no raw tempdir path appears.
            assert td not in text, "Output contains absolute path"

    def test_oneshot_measures_current_state(self):
        with tempfile.TemporaryDirectory() as td:
            out_path = os.path.join(td, "peak.json")
            test_file = os.path.join(td, "test.txt")
            with open(test_file, "w") as f:
                f.write("x" * 1000)
            subprocess.run(
                [sys.executable, str(CAP_SCRIPTS / "peak_sampler.py"),
                 "--root", f"test={td}", "--interval-seconds", "2",
                 "--oneshot", "--output", out_path],
                capture_output=True, timeout=10
            )
            data = json.loads(open(out_path).read())
            pd = data.get("peak_deltas", {}).get("test", {})
            # Oneshot: baseline == peak, delta = 0
            assert pd.get("peak_logical_bytes", 0) >= 1000
            assert pd.get("peak_delta_logical_bytes", 0) == 0
            assert len(data.get("samples", [])) == 1

    def test_symlink_skipped(self):
        from scripts.capacity.calibration.peak_sampler import _collect
        with tempfile.TemporaryDirectory() as td:
            real_file = os.path.join(td, "real.txt")
            link_file = os.path.join(td, "link.txt")
            subdir = os.path.join(td, "sub")
            link_dir = os.path.join(td, "linkdir")
            os.mkdir(subdir)
            with open(real_file, "w") as f:
                f.write("x" * 100)
            with open(os.path.join(subdir, "data.txt"), "w") as f:
                f.write("y" * 200)
            os.symlink("real.txt", link_file)
            os.symlink(subdir, link_dir)
            logical, allocated = _collect(td, follow_symlinks=False)
            # Counts real.txt (100) + sub/data.txt (200) but not link.txt or linkdir
            assert logical == 300, f"Expected 300, got {logical}"

    def test_deterministic_json_structure(self):
        with tempfile.TemporaryDirectory() as td:
            known_file = os.path.join(td, "data.bin")
            with open(known_file, "wb") as f:
                f.write(b"x" * 512)
            out1 = os.path.join(td, "p1.json")
            out2 = os.path.join(td, "p2.json")
            for out in (out1, out2):
                subprocess.run(
                    [sys.executable, str(CAP_SCRIPTS / "peak_sampler.py"),
                     "--root", f"test={td}", "--interval-seconds", "2",
                     "--oneshot", "--output", out],
                    capture_output=True, timeout=10
                )
            d1 = json.loads(open(out1).read())
            d2 = json.loads(open(out2).read())
            # Check structural equality (keys, types) not exact values
            assert set(d1.keys()) == set(d2.keys())
            assert d1["tool"] == d2["tool"]
            assert d1["schema_version"] == d2["schema_version"]
            assert d1["interval_seconds"] == d2["interval_seconds"]
            assert d1["sample_count"] == d2["sample_count"]
            assert d1["roots"] == d2["roots"]
            # Validate both have same peak_delta structure
            for name in d1["peak_deltas"]:
                assert set(d1["peak_deltas"][name].keys()) == set(d2["peak_deltas"][name].keys())

    def test_allocated_bytes_present(self):
        with tempfile.TemporaryDirectory() as td:
            out_path = os.path.join(td, "peak.json")
            with open(os.path.join(td, "a.txt"), "w") as f:
                f.write("x" * 500)
            subprocess.run(
                [sys.executable, str(CAP_SCRIPTS / "peak_sampler.py"),
                 "--root", f"test={td}", "--interval-seconds", "2",
                 "--oneshot", "--output", out_path],
                capture_output=True, timeout=10
            )
            data = json.loads(open(out_path).read())
            pd = data.get("peak_deltas", {}).get("test", {})
            # allocated_bytes might be None on some filesystems
            assert "peak_allocated_bytes" in pd

    def test_tool_and_schema(self):
        with tempfile.TemporaryDirectory() as td:
            out_path = os.path.join(td, "peak.json")
            subprocess.run(
                [sys.executable, str(CAP_SCRIPTS / "peak_sampler.py"),
                 "--root", f"test={td}", "--interval-seconds", "2",
                 "--oneshot", "--output", out_path],
                capture_output=True, timeout=10
            )
            data = json.loads(open(out_path).read())
            assert data.get("tool") == "peak_sampler"
            assert data.get("schema_version") == "1.0"

    def test_no_file_names_in_output(self):
        with tempfile.TemporaryDirectory() as td:
            out_path = os.path.join(td, "peak.json")
            with open(os.path.join(td, "secret.txt"), "w") as f:
                f.write("sensitive")
            subprocess.run(
                [sys.executable, str(CAP_SCRIPTS / "peak_sampler.py"),
                 "--root", f"test={td}", "--interval-seconds", "2",
                 "--oneshot", "--output", out_path],
                capture_output=True, timeout=10
            )
            data = json.loads(open(out_path).read())
            text = json.dumps(data)
            assert "secret.txt" not in text
            assert "sensitive" not in text
