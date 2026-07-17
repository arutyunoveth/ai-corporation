"""Create the R4 blind candidate pool without downloading or analysing documents."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.modules.tender_operator_agent_demo.settings import get_zakupki_soap_settings
from src.modules.tender_operator_agent_demo.zakupki_soap_client import ZakupkiSoapClient


ROOT = Path(__file__).resolve().parents[2]
POOL = ROOT / "output/r4/blind_candidate_pool.csv"
CASE_SET = ROOT / "docs/r4/blind_case_set.yaml"
FREEZE = ROOT / "docs/r4/blind_case_set_freeze.md"
API_URL = "http://127.0.0.1:8001/api/demo/tender-agent/procurement/public-44fz-search"
R3_SMOKE_CASES = {"0116300036226000029", "0116300036226000030"}

CATEGORIES = (
    ("standard_goods", "Поставка", 12),
    ("electrical_goods", "кабель", 10),
    ("food", "продукты питания", 10),
    ("medical_or_household", "медицинские изделия", 10),
    ("medical_or_household", "хозяйственные товары", 10),
    ("complex_multiline", "оборудование", 10),
    ("random_goods", "товары", 10),
)

CASE_QUOTAS = {
    "standard_goods": 6,
    "electrical_goods": 4,
    "food": 3,
    "medical_or_household": 3,
    "complex_multiline": 2,
    "random_goods": 2,
}


def _used_numbers() -> set[str]:
    locations = [ROOT / "docs/r3", ROOT / "docs/r4", ROOT / "output/review-batches", ROOT / "tests/fixtures"]
    found = set(R3_SMOKE_CASES)
    for location in locations:
        if not location.exists():
            continue
        for path in location.rglob("*"):
            if path.is_file() and path != POOL:
                found.update(re.findall(r"\b\d{19}\b", path.read_text(errors="ignore")))
    return found


def _search(query: str) -> list[dict]:
    payload = urlencode({"query": query, "max_results": 50, "page_size": 50}).encode()
    request = Request(API_URL, data=payload, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urlopen(request, timeout=90) as response:  # noqa: S310 -- local UI endpoint
        return json.loads(response.read()) .get("cards", [])


def _plain(value: object) -> str:
    return re.sub(r"<[^>]+>", "", str(value or "")).replace("\n", " ").strip()


def _is_goods(card: dict) -> bool:
    title = _plain(card.get("title")).lower()
    return bool(title) and not any(word in title for word in ("оказание услуг", "выполнение работ", "техническое обслуживание", "ремонт"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def main() -> int:
    if CASE_SET.exists():
        raise SystemExit(f"refusing to overwrite frozen case set: {CASE_SET}")
    used = _used_numbers()
    client = ZakupkiSoapClient(get_zakupki_soap_settings())
    if not client.is_configured():
        raise SystemExit("getDocsIP is not configured")

    rows: list[dict[str, str]] = []
    eligible: list[dict[str, str]] = []
    seen: set[str] = set()
    order = 0
    for category, query, limit in CATEGORIES:
        accepted = 0
        for card in _search(query):
            if accepted >= limit:
                break
            order += 1
            number = str(card.get("notice_number") or card.get("reestr_number") or "").strip()
            row = {
                "collection_order": str(order), "query": query, "category": category,
                "registry_number": number, "title": _plain(card.get("title")),
                "customer": _plain(card.get("customer_name")),
                "publication_date": str(card.get("publication_date") or ""),
                "source_page": "public-44fz-search", "cursor_batch": "backfill-50",
                "previously_used": "false", "documents_available": "false", "documents_count": "0",
                "selection_status": "excluded", "exclusion_reason": "",
            }
            if not re.fullmatch(r"\d{19}", number):
                row["exclusion_reason"] = "invalid_card"
            elif number in used:
                row["previously_used"] = "true"
                row["exclusion_reason"] = "previously_used"
            elif number in seen:
                row["exclusion_reason"] = "duplicate_registry_number"
            elif not _is_goods(card):
                row["exclusion_reason"] = "not_goods"
            else:
                seen.add(number)
                try:
                    docs = client.get_docs_by_reestr_number(number)
                    document_count = len(docs.archive_urls)
                except Exception:  # no archive download and no analysis; only availability is recorded
                    document_count = 0
                if document_count:
                    row.update(documents_available="true", documents_count=str(document_count), selection_status="eligible")
                    eligible.append(row)
                    accepted += 1
                else:
                    row["exclusion_reason"] = "documents_unavailable"
            rows.append(row)

    if len(eligible) < 40:
        raise SystemExit(f"eligible candidate pool is insufficient: {len(eligible)} < 40")
    selected: list[dict[str, str]] = []
    for category, quota in CASE_QUOTAS.items():
        choices = [row for row in eligible if row["category"] == category]
        if len(choices) < quota:
            raise SystemExit(f"not enough candidates for {category}: {len(choices)} < {quota}")
        selected.extend(choices[:quota])
    if len(selected) != 20 or len({row["registry_number"] for row in selected}) != 20:
        raise SystemExit("case-set selection is not 20 unique candidates")

    POOL.parent.mkdir(parents=True, exist_ok=True)
    with POOL.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    pool_hash = _sha256(POOL)
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    baseline = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    lines = [
        "revision: 1", f"created_at: {_yaml_quote(now)}", f"baseline_sha: {_yaml_quote(baseline)}",
        "selection_completed_before_analysis: true", f"candidate_pool_sha256: {_yaml_quote(pool_hash)}", "cases:",
    ]
    for review_order, row in enumerate(selected, start=1):
        lines.extend([
            f"  - review_order: {review_order}", f"    procurement_number: {_yaml_quote(row['registry_number'])}",
            f"    category: {_yaml_quote(row['category'])}", f"    selection_reason: {_yaml_quote('new eligible public goods candidate from ' + row['query'])}",
            f"    publication_date: {_yaml_quote(row['publication_date'])}", "    previously_used: false",
            "    documents_available: true", "    analysis_started: false",
        ])
    CASE_SET.write_text("\n".join(lines) + "\n", encoding="utf-8")
    case_hash = _sha256(CASE_SET)
    FREEZE.write_text(
        "# R4 blind case-set freeze\n\n"
        f"- Frozen at: `{now}`\n- Branch: `codex/r3-operator-pilot`\n- Baseline SHA: `{baseline}`\n"
        f"- Candidate pool SHA-256: `{pool_hash}`\n- Case set SHA-256: `{case_hash}`\n"
        f"- Eligible candidates: `{len(eligible)}`\n- Frozen cases: `20`\n\n"
        "The selection was completed before any analysis. Availability was checked only through getDocsIP; archives were not downloaded, documents were not read, and no case was selected by report quality.\n",
        encoding="utf-8",
    )
    print(json.dumps({"eligible": len(eligible), "rows": len(rows), "pool_sha256": pool_hash, "case_set_sha256": case_hash}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
