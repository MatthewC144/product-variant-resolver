# Domain ranker v2 remediation — Lite QA review

Date: 2026-10-10. Scope: **DRV2-T1–T5**. Verdict: **T5 TRAINING/RELEASE PASS; T6 NOT AUTHORIZED**.

## Coverage

| Requirement | Evidence | Result |
|---|---|---|
| DRV2-R1 | Owner statement digest, exact source/denylist/T5/code hashes and narrow permissions | PASS |
| DRV2-R2 | 153 positive identities and 173 combined query hashes denied | PASS |
| DRV2-R3 | 180 unique queries/identities/families frozen as 120/30/30 | PASS |
| DRV2-R4 | 112 train queries have at least two query-supported same-casting wrong-release siblings | PASS |
| DRV2-R5 | One preregistered RankNet-style objective, fixed recipe and two seeds | PASS |
| DRV2-R6 | Validation and untouched selection are distinct family-disjoint partitions | PASS |
| DRV2-R7 | 180 query-only Top-25 pools, 4,500 candidates, zero misses/injections | PASS |
| DRV2-R8 | T3 p95 `217.699834 ms` failed; equivalent ONNX T3R p95 `103.654042 ms` | PASS after repair |
| DRV2-R11 | Public artifacts contain aggregate data only; row-level packs remain ignored/mode `0600` | PASS |
| DRV2-R12 | Owner-attested and community-catalog-relative limitations retained | PASS |

Thirty-four focused T1–T5 tests, Ruff, strict MyPy, CLI check mode and `git diff --check` pass.
The authoring protocol fixes field projection, deterministic templates/order, 120/30/30 minima,
same-family density requirements and output isolation. It explicitly prohibits resolver output and
T5-error access during authoring.

A whole-repository smoke run was also attempted, but was stopped after 13 failures and 105 passes
because the committed T49.3 experimental human-storage app cannot initialize: its independent v4
protocol reports `src/product_variant_resolver/retrieval.py` as stale. T4 does not modify that file,
the v4 protocol or the storage app, and its focused lineage remains green. This is disclosed as
pre-existing repository baseline debt rather than being silently counted as a T4 pass.

## Findings and carry-forward

The initial quick audit counted 1,040 eligible rows because it used case folding only. The committed
implementation uses the project's `normalize_text` contract, which merges equivalent casting forms
and correctly yields 1,041 rows. Specs and tests were corrected before materialization.

The source snapshot still records `staging_only_not_evaluation_or_canonical` and lacks independently
verified rights metadata. T1 does not silently change the source. Its overlay records the owner's
bounded authorization and keeps labels community-catalog-relative rather than manufacturer truth.

T2 produced a local-only mode-0600 pack with content SHA-256
`149d7d867b9e270ffb805906aec64685d6823f11efcd68a59e9e74ba60134e6f`. All 180 queries, identities
and families are unique; cross-partition query, identity and family overlap are zero. Each of the 120
train rows belongs to a family with at least two other eligible releases, but T2 created zero
candidate labels. Public manifests contain aggregate counts and hashes only.

T3's 90 validation samples measured p50 `183.735 ms` and p95 `217.699834 ms`. The 200 ms ceiling
was frozen before execution, so the readiness result is FAIL even though pools and integrity checks
passed. No selection quality metric, hard-negative label, training run, calibration, final evaluation
or runtime change occurred.

T3R preserved all 180 complete Top-25 orderings; maximum absolute logit delta was
`1.4781951904296875e-05`, below the frozen `2e-5` tolerance. The identical 90-sample protocol then
measured p50 `88.765583 ms` and p95 `103.654042 ms`, passing the unchanged 200 ms budget. The 91 MB
float32 ONNX graph is reproducible but remains local-only to avoid repository bloat.

T4 uses no validation or selection labels. It admits 112/120 train queries and materializes 332
triples. Nineteen same-casting siblings lack any conflict on fields supported by the frozen query
template; eight other defensible siblings belong to one-negative queries. All 27 remain held rather
than being forced into binary labels. The local artifact is mode `0600` and ignored; public files
contain only the Owner Gate, hashes, policy and aggregate counts.

T4 established exact-release training-data readiness without a model-quality claim. At that
checkpoint, training and checkpoint release were still unauthorized; the separately gated T5 run
below supersedes only those two pending items.

T5 trained exactly two seeds with the preregistered recipe. Seed 17 selected epoch 2 and seed 29
selected epoch 3; both best validation MRR@10 values are `0.95`. The package contains only two
float16 safetensors files and an exact support-file allowlist, passes strict tensor inspection and
offline loading, and excludes optimizer/pickle state. Selection, test, no-match, calibration, final
evaluation and runtime counters remain zero.

This PASS establishes reproducible pairwise fine-tuning and safe checkpoint release. It does not
establish that either domain checkpoint beats generic. T6 must apply the still-unseen selection
partition and frozen qualification rules in one separately authorized run.
