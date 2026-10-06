# Portfolio evidence refresh v2 — QA review

Date: 2026-10-05. Mode: Lite / Lean Industrial. Verdict: **PASS — documentation refresh**.

## Requirement evidence

| Requirement | Evidence | Result |
|---|---|---|
| PER-R1 | README opening names 1,763 releases, 153 image-search-derived positives, 100/53 split and 20 negatives. | PASS |
| PER-R2 | Diagram and prose show canonical retrieval, optional Pointwise, frozen policy, three outcomes and Human Knowledge authority isolation. | PASS |
| PER-R3 | 53-case table matches final-comparison JSON: RRF 29 exact, Pointwise 36, Listwise 32 and all raw denominators. | PASS |
| PER-R4 | Policy table matches balanced result: 5/5, 5/53, 3/53, 11/20, 0/20 and 54/73; runtime HOLD is visible. | PASS |
| PER-R5 | Fixture `winner: null` and its immutable report remain linked as the saturated first experiment. | PASS |
| PER-R6 | Source/query/prior-use/coverage/default-runtime/production limitations are explicit. | PASS |
| PER-R7 | Portfolio Guide has exactly three resume bullets, one pitch, four review steps, guardrails, stack and next step. | PASS |
| PER-R8 | Link scan finds 66 README and 14 Portfolio Guide local links; missing targets: 0. | PASS |
| PER-R9 | Working diff is limited to README, Portfolio Guide, Project Log, decision and v2 spec documentation. | PASS |
| PER-R10 | Project Log records the new evidence hierarchy, file changes and precision/coverage disclosure decision. | PASS |

## Metric verification

Automated JSON comparison confirms the displayed frozen-test counts against
`development-selection.json`, `final-comparison.json` and the balanced holdout `results.json`.
Pointwise exact Top-1 delta is 7/53 = 13.21 percentage points; positive accepted exact precision is
5/5 while exact recall is 5/53; combined abstention is 54/73. The README never converts these into a
production-accuracy claim.

## Static verification

README H2 order remains problem-first and places setup after evidence/limitations. The Portfolio
Guide resume section contains exactly three Markdown bullets. Searches confirm `hashing-v1` remains
non-neural, Pointwise is development-only, no LLM generates the answer, and runtime stays held.
All relative links resolve and `git diff --check` passes.

## Finding

The refreshed portfolio story is materially stronger and more honest than the old fixture-first
version: it demonstrates a measured neural ranking gain on a harder catalog, then shows why that gain
still did not justify deployment after calibration. No product behavior or evidence artifact changed.
