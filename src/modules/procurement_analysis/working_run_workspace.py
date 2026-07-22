"""Storage-neutral working-run locations for the frozen procurement producer."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from src.tender_research.config import load_config

_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


@dataclass(frozen=True)
class WorkingRunPaths:
    root: Path
    input_dir: Path
    normalized_dir: Path
    output_dir: Path
    procurement_dir: Path
    metadata_path: Path
    events_path: Path


class WorkingRunWorkspace:
    def __init__(self, run_id: str, paths: WorkingRunPaths):
        self.run_id, self.paths = run_id, paths

    def ensure(self) -> None:
        for path in (self.paths.root, self.paths.input_dir, self.paths.normalized_dir, self.paths.output_dir, self.paths.procurement_dir):
            path.mkdir(parents=True, exist_ok=True)

    def load_metadata(self) -> dict:
        return json.loads(self.paths.metadata_path.read_text(encoding="utf-8"))

    def save_metadata(self, metadata: dict) -> None:
        self.ensure(); self.paths.metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def append_event(self, event_type: str, message: str, details: dict | None = None) -> None:
        self.ensure()
        with self.paths.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"type": event_type, "message": message, "details": details or {}}, ensure_ascii=False) + "\n")


class CustomerPilotWorkingRunWorkspace(WorkingRunWorkspace):
    def __init__(self, customer_id: str, project_id: str, case_id: str, run_id: str):
        values = (customer_id, project_id, case_id, run_id)
        if any(not _SAFE.fullmatch(value) for value in values):
            raise ValueError("Unsafe customer working-run segment")
        root = Path(load_config().data_dir).resolve() / "customer-pilot" / customer_id / project_id / case_id / run_id / "working"
        super().__init__(run_id, WorkingRunPaths(root, root / "input", root / "normalized", root / "output", root / "procurement", root / "metadata.json", root / "events.jsonl"))
