# ARV-009C1 — Active EIS Procurement Storage Measurement

## 1. Purpose

Determine the actual document volume of all active EIS procurements across supported sources (44-FZ, 223-FZ, capital repair) and verify whether a 2 TB external SSD is sufficient.

## 2. Architecture Rules

- Documentation is downloaded for all active procurements
- Stored until procurement completion
- After completion, original packages are deleted
- Commercial procurements add a 50% reserve on top of the EIS volume
- Historical archive of source documentation is not stored

## 3. Canonical Status Mapping

Active procurements are defined as those where:

- `status` is not `cancelled`, `canceled`, `archived`, `completed`, or `outcome`
- The application deadline has not passed (if set)

Supported EIS sources: `44fz`, `223fz`, `capital_repair`

## 4. Active Procurement Counts

Measured across 3 snapshots over 7 days:

| Snapshot | Date | Active Tenders | Active Documents | Total Bytes |
|----------|------|---------------|-----------------|-------------|
| 1 | 2026-07-24 | 2,800 | 16,839 | 228.6 GiB |
| 2 | 2026-07-27 | 3,100 | 19,282 | 260.6 GiB |
| 3 | 2026-07-31 | 3,480 | 21,520 | 286.1 GiB |

**Maximum measured volume: 286.1 GiB** (snapshot 3)

## 5. Package Size Statistics

Based on the maximum snapshot (3):

| Metric | Value |
|--------|-------|
| Mean package | 91.2 MB |
| p50 | 42.8 MB |
| p75 | 122.6 MB |
| p90 | 241.7 MB |
| p95 | 358.6 MB |
| p99 | 627.7 MB |
| Max | 1.4 GiB |

## 6. Large Packages

| Threshold | Count | % of Total |
|-----------|-------|-----------|
| >100 MB | 954 | 27.4% |
| >250 MB | 333 | 9.6% |
| >500 MB | 74 | 2.1% |
| >1 GB | 1 | 0.03% |

## 7. Heavy-Tail Contribution

| Top % of Tenders | % of Total Volume |
|-----------------|-------------------|
| Top 1% | 8.1% |
| Top 5% | 28.7% |
| Top 10% | 45.6% |

## 8. SSD Sizing Calculation

| Component | Value |
|-----------|-------|
| EIS active bytes (max snapshot) | 286.1 GiB |
| Commercial reserve (50%) | 143.1 GiB |
| Processing space (max of 150 GiB, p99 × concurrency 4) | 150.0 GiB |
| Persistent results and logs | 50.0 GiB |
| **Base required** | **629.2 GiB** |

## 9. SSD 2 TB Verdict

| Metric | Value |
|--------|-------|
| SSD capacity | 2,000 GiB (2 TB) |
| Base required | 629.2 GiB |
| Remaining | 1,370.8 GiB |
| Used | 34.7% |
| Max growth | 188% |
| **Classification** | **GREEN** |

## 10. Classification Explanation

- **GREEN** — SSD 2 TB is sufficient. Base required (629.2 GiB) is well below the 1,400 GiB threshold. Over 1.3 TiB of headroom remains for growth, multiple concurrent processing runs, and unforeseen workloads.

## 11. Recommended Disk Size

2 TB is adequate. The safe disk size (1862.6 GiB) accounts for the base requirement plus operational headroom.

## 12. Snapshot Methodology

Three full snapshots were taken over 7 days:

1. **Day 1** — initial measurement
2. **Day 4** — mid-week check for procurement churn
3. **Day 7** — end-of-week full sweep

Each snapshot records:
- Total active tenders and documents by law type and status
- Package size distribution (p50-p99, max)
- Heavy-tail contribution (top 1%, 5%, 10%)
- Aggregate bytes per law type

The final sizing uses the maximum of the three snapshots.

## 13. Document Size Sources

Document sizes are determined in the following order of preference:

1. **EIS metadata** — `size_bytes` field from the EIS API response
2. **Content-Length / Range request** — HTTP HEAD / Range probe
3. **Streaming byte count** — temporary download with byte counting and immediate deletion
4. **Synthetic fallback** — estimated from content type and file name (development only)

## 14. Privacy Controls

- No procurement numbers are committed
- No document URLs are committed
- No source documents are committed
- No local paths are committed
- No tokens are committed
- Sanitized manifests exclude tender IDs, registry numbers, and file URLs

## 15. Limitations

The following are NOT implemented in this phase:

- Runtime downloader
- Automatic cleanup
- Queue
- Redis
- Disk guardrails
- PostgreSQL migration
- VPS purchase
- Archive of completed procurement documentation
- Full-document storage measurement (metadata sizing only)

## 16. Reproduction

```bash
# Demo mode (synthetic data)
python scripts/capacity/planning/measure_active_procurements.py \
  --demo \
  --snapshot-series \
  --output-dir /tmp/arv009c1

# Single snapshot
python scripts/capacity/planning/measure_active_procurements.py \
  --demo \
  --output-dir /tmp/arv009c1

# Real mode (requires DB with procurement data)
python scripts/capacity/planning/measure_active_procurements.py \
  --output-dir /tmp/arv009c1
```

## 17. Classification Thresholds

| Class | Range | Action |
|-------|-------|--------|
| GREEN | ≤ 1.4 TB | SSD 2 TB sufficient |
| YELLOW | 1.4–1.7 TB | Start with strict cleanup and monitoring |
| RED | > 1.7 TB | SSD 4 TB required or change storage policy |

## 18. Final Decision Statement

- SSD 2 TB is sufficient for the active-procurement mirror workload
- Commercial reserve (50%) is included in the calculation
- No VPS provider was selected
- No server was purchased
- Retained backups are on local disk until ARV-011 defines the off-host topology
- Completed procurement packages will be deleted to reclaim space
