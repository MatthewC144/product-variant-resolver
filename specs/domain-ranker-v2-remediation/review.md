# Domain ranker v2 remediation — Lite QA review

Date: 2026-10-09. Scope: **DRV2-T1 only**. Verdict: **PASS for governance; T2+ not authorized**.

## Coverage

| Requirement | Evidence | Result |
|---|---|---|
| DRV2-R1 | Owner statement digest, exact source/denylist/T5/code hashes and narrow permissions | PASS |
| DRV2-R2 | 153 positive identities and 173 combined query hashes denied | PASS |
| DRV2-R3 | 1,041 eligible rows across 269 families, exceeding 180-query capacity minimum | PASS readiness only |
| DRV2-R11 | Three aggregate JSON files; no row-level query, identity, label, URL or local path | PASS |
| DRV2-R12 | Owner-attested and community-catalog-relative limitations retained | PASS |

Ten v2-governance/comparison tests, Ruff, strict MyPy, CLI check mode and `git diff --check` pass.
The authoring protocol fixes field projection, deterministic templates/order, 120/30/30 minima,
same-family density requirements and output isolation. It explicitly prohibits resolver output and
T5-error access during authoring.

## Findings and carry-forward

The initial quick audit counted 1,040 eligible rows because it used case folding only. The committed
implementation uses the project's `normalize_text` contract, which merges equivalent casting forms
and correctly yields 1,041 rows. Specs and tests were corrected before materialization.

The source snapshot still records `staging_only_not_evaluation_or_canonical` and lacks independently
verified rights metadata. T1 does not silently change the source. Its overlay records the owner's
bounded authorization and keeps labels community-catalog-relative rather than manufacturer truth.

DRV2-T2 requires a separate Owner Gate. Until then no 180-query dataset, split, candidate pool,
negative triple, model checkpoint or evaluation may be produced.
