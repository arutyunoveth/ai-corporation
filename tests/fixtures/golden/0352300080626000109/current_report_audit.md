# Current report audit

## Metadata

Audited web baseline: `tmp/r1/0352300080626000109/baseline/toa-runs/toa-run-20260714090052-5eb0fd/output/report.html`.
The corresponding JSON report was generated at `2026-07-14T09:01:19Z`.
No DOCX or PDF output was retained in the baseline; parity for those formats is
therefore **N/A / not verifiable**, not a pass.

## Automatic FAIL

- S0: the NMCK service catalogue is absent.
- S0: the report renders unsupported claims about training, SMEV/ERN and
  education resources.
- S1: subject is rendered as a generic EIS documentation package rather than
  the evidenced vehicle-repair service subject.

## Scores

| Layer | Score | Reason |
| --- | ---: | --- |
| Extraction | 0/3 | DOCX table became flattened text; no positions were produced. |
| Analysis | 0/3 | Wrong generic subject and unsupported factual inferences. |
| Report | 0/3 | No service catalogue; no retained DOCX/PDF parity evidence. |

Weighted score: **0/3; automatic FAIL**.

## Evidence trail

`notice-xml` proves the service subject and OKPD2 45.20. `nmck-docx` proves a
unit-price service table, a conditional unit/norm-hour definition and the
maximum contract price. The report accurately shows 500,000 RUB, but it does
not show the source catalogue and must not be treated as golden truth.

## Requirements created

See `defects_baseline.yaml`: EXTR-001, ANL-001, RPT-001 and ANL-002. Future
acceptance must validate evidence ownership and HTML/DOCX/PDF parity.
