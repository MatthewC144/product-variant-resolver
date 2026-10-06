# AI eval evidence — Pointwise no-match holdout v1

Date: 2026-10-05. Evaluation: PNMH-G2. Result artifact SHA-256:
`937eabc88164532ce686d5c1d4521d0ffef58efc2691d8836cba723fd68b05c6`.

## Rubric and evidence

| Dimension | Frozen criterion | Observed | Verdict |
|---|---|---|---|
| Binding integrity | All approved data/policy and transitive model/catalog hashes match before and after the run. | All seven frozen content hashes matched. | PASS |
| Rejection utility | At least 5 of 20 known catalog-relative negatives return `no_match`. | 11/20; recall 55%. | PASS |
| False-match safety | At most 2 of 20 known negatives return `matched`. | 0/20; false-match rate 0%. | PASS |
| Honest abstention | `ambiguous` is counted separately and never relabeled as success. | 9/20; abstention rate 45%. | PASS |
| Output blindness | No row-level query, ID, expected identity, candidate, confidence or prediction is persisted. | Aggregate counters, reason counts and confidence min/mean/max only. | PASS |
| No adaptation | Dataset truth/membership, model, feature schema and thresholds do not change. | All guardrails false and parent hashes unchanged. | PASS |
| Runtime boundary | Evaluation cannot enable or change runtime behavior. | Runtime authorization/default remain false. | PASS |

## Interpretation boundary

The result demonstrates that the frozen Pointwise v2 policy made no false matches on this small
catalog-relative negative holdout while explicitly rejecting 55% and abstaining on the remainder.
It does not establish global product absence, exact-release accuracy on catalog-present queries,
production traffic quality or statistical confidence at large scale. Because row-level outputs are
not retained, the 20 test rows remain unavailable for error-driven retuning.
