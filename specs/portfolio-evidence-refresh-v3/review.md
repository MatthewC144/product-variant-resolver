# Portfolio evidence refresh v3 — QA review

Date: 2026-10-10. Mode: Lite / Lean Industrial. Verdict: **PASS — documentation refresh**.

## Requirement evidence

| Requirement | Evidence | Result |
|---|---|---|
| PER3-R1 | README names 150 targets, 300 paired records and the grouped 100/50 split. | PASS |
| PER3-R2 | README and Portfolio Guide match the frozen combined Top-1, MRR and Recall metrics. | PASS |
| PER3-R3 | Both documents call `n=100` source observations from 50 identities, not 100 independent products. | PASS |
| PER3-R4 | Dual-source ranking and prior policy results remain separate; runtime remains HOLD. | PASS |
| PER3-R5 | Portfolio Guide retains exactly three primary resume bullets and updates the pitch, review path, guardrails and next step. | PASS |
| PER3-R6 | Repository-relative link scan reports zero missing targets. | PASS |
| PER3-R7 | Diff contains Markdown documentation/specification only; no source, data, model or runtime file changed. | PASS |
| PER3-R8 | Project Log records the problem, edits, evidence choices and runtime boundary. | PASS |

## Metric and content verification

The displayed combined final numbers were compared with
`data/evaluation/serper-dual-source-evaluation-v1/raw-pointwise-final-test.json`: RRF versus
Pointwise exact Top-1 is 55% versus 64%, casting Top-1 is 86% versus 95%, MRR@10 is 0.722 versus
0.792, Recall@10 is 99% versus 98%, and Recall@25 remains 99%. The artifact confirms 50 test
targets and 100 source observations, no calibration/policy evaluation, no threshold or runtime
change, and no permitted rerun.

The original calibrated-policy evidence remains independently described as accepted positive
precision `5/5`, negative false matches `0/20`, and combined abstention `54/73` (73.97%). No new
ranking percentage is presented as policy accuracy or production performance.

## Static verification

Automated checks confirmed all local Markdown links resolve, exactly three primary resume bullets
exist, expected claims appear in both documents, no credential pattern was introduced, and
`git diff --check` passes. The changed paths are README, Portfolio Guide, Project Log and this v3
documentation pair only.

## Finding

The repository now leads with its strongest current ranking evidence while preserving the less
favorable Recall@10 movement and low-coverage policy result. This improves portfolio clarity without
changing system behavior or consuming the final test as tuning data.
