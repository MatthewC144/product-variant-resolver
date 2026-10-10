# Domain ranker v2 hard-negative readiness — AI-eval rubric

Date: 2026-10-10. Scope: DRV2-T4. Verdict: **EXACT-RELEASE EVIDENCE DENSITY PASS; NO MODEL-QUALITY CLAIM**.

| Rubric | Evidence | Result |
|---|---|---|
| Frozen lineage | T2 query pack, T3 pools and passing T3R result are exact SHA-256 bindings | PASS |
| Train-only scope | 120 train pools processed; validation/selection label-read counts both 0 | PASS |
| Positive integrity | Every target UUID is unique in its Top-25 and all six rendered identity fields match | PASS |
| Label authority | Same casting plus at least one query-template-supported exact-field conflict | PASS |
| Evidence density | 112 queries have at least two defensible siblings; minimum is 60 | PASS |
| Pairwise output | 332 deterministic query/positive/negative triples | PASS |
| Ambiguity handling | 19 ambiguous siblings plus 8 one-negative-query siblings remain held | PASS |
| Selection isolation | training runs 0; selection quality evaluations 0 | PASS |
| Publication boundary | row-level pack ignored/mode `0600`; Git output is aggregate-only | PASS |

Generic pointwise rank is used only to provide a deterministic audit order after a sibling has
already passed evidence rules. It is never treated as ground truth. A different UUID is likewise
insufficient by itself: the query must expose a field that distinguishes the target from the
sibling. This is why 27 records remain held instead of being converted into easy but weak labels.

The 332 triples are frozen-community-catalog-relative training evidence, not Mattel/manufacturer or
global truth. T4 proves that the pairwise experiment has enough auditable exact-release comparisons.
It does not prove that fine-tuning improves ranking and does not authorize T5 training, checkpoint
release, selection scoring, calibration, final evaluation or runtime activation.
