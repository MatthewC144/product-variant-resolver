# Identity-Bounded Human Knowledge Retrieval — Requirements

Date: 2026-09-13. Mode: Lite / Lean Industrial.
Status: proposed; project-owner confirmation required before implementation or retrieval.
Proposed experimental version: `human-knowledge-hybrid-v4`.

## Purpose

Address the v3 development failure through a new architecture decision, not a wider threshold
search: prevent generic listing words from admitting documents independently of casting identity,
and replace query-window × document-form comparisons with direct normalized posting accumulation.
Keep Dual RAG authority, original safety/quality budgets and independent-final-evaluation lifecycle.
This is not a neural model, database expansion or a claim that v4 already works.

## Requirements

### IBR-R1 — Preserve historical evidence and code provenance

WHILE v4 is developed, THE SYSTEM SHALL leave the original v1 final benchmark/report, frozen 199-case
development pack/manifest, v3 selection JSON/Markdown and their source-bound implementation files
unchanged; v1 SHALL NOT be loaded for fitting or selection. The v3 development report MAY be used
as disclosed diagnostic/before evidence, never as independent final accuracy.

### IBR-R2 — Freeze a new protocol before v4 output

WHEN implementation begins after owner confirmation, THE SYSTEM SHALL commit a checksum-bound
protocol containing this design, corpus/development hashes, observed-v3-development reuse disclosure,
identity/noise policy, score formula, grid, work limits, selection gates and cost workload before
any v4 configuration output is viewed. The old pack's pre-output declarations SHALL remain historical
v3 declarations, not be presented as a fresh blind v4 dataset.

### IBR-R3 — Limit admission fields to casting identity

WHEN v4 builds admission indexes, THE SYSTEM SHALL use only `casting` for provisional variants and
`casting` plus approved `aliases` for review families; it SHALL NOT admit from brand, human-label
listing strings, pricing terms, initial recognition names, series/variant labels, URLs, source IDs
or decision reasons. Existing broad text MAY affect dense ordering only after identity admission.

### IBR-R4 — Apply one disclosed identity-noise policy

WHEN admission forms and query forms are normalized, THE SYSTEM SHALL use the same NFKC/casefold/token
normalizer and frozen whole-token noise set, preserve meaningful alphanumeric/numeric identity tokens,
and reject empty identity cores at index construction. It SHALL NOT add per-case rules, target IDs,
query rewriting or noise exceptions after output viewing. Empty/noise-only queries SHALL return no
Human Knowledge candidate without consulting broad sparse/dense evidence.

### IBR-R5 — Require complete exact identity evidence for token admission

WHEN token admission runs, THE SYSTEM SHALL require every token of at least one nonempty approved
identity core to occur in the query core; a single generic or partial identity token SHALL NOT be
sufficient. Typos and spacing variations MAY enter independently through qualified character evidence.
Sparse evidence SHALL be computed from identity cores and precomputed token postings/IDF, not broad
listing fields or per-query corpus-frequency scans.

### IBR-R6 — Accumulate exact character scores from form-level postings

WHEN character retrieval runs, THE SYSTEM SHALL index normalized spaced/compact bigram/trigram
TF-IDF identity vectors per stable form ID, accumulate cosine dot products directly from weighted
gram postings, and take the maximum form/window score per document. Unseen query grams SHALL count
in the query norm using the frozen maximum-IDF rule, preventing scores inflated by discarding unknown
text. It SHALL NOT perform the old window × every eligible document-form Cartesian comparison.

### IBR-R7 — Bound work without publishing partial ranks

WHEN query or posting work exceeds a declared limit, THE SYSTEM SHALL return no Human Knowledge
candidates and expose a debug-only budget-abstention reason/counters; it SHALL NOT publish a partial
ranking, silently truncate queries, fabricate scores or change canonical status. Index limits SHALL
fail readiness rather than discard approved identity forms.

### IBR-R8 — Preserve three-source fusion without type quotas

WHEN ranking admitted documents, THE SYSTEM SHALL retain at most 25 exact-identity token and 25
qualified character candidates, dense-rank only their union with `hashing-v1`/192 dimensions, and
fuse sparse/dense/character ranks with RRF k=60 and missing-rank contribution zero. Ties SHALL use
knowledge UUID; no family reservation or provisional quota SHALL be introduced.

### IBR-R9 — Use the predeclared architecture-only selection grid

WHEN development selection executes, THE SYSTEM SHALL run exactly the same seven floors
`0.25,0.30,0.35,0.40,0.45,0.50,0.55` × three character weights `0.5,1.0,1.5`, sparse/dense weights
1 and K=5, under the new protocol/report version. It SHALL retain all 4,179 raw case/configuration
outputs, work counters and any abstentions. No other policy value SHALL be fitted during that run.

### IBR-R10 — Retain all development selection gates

WHEN selecting a winner, THE SYSTEM SHALL require positive Recall@5 ≥0.90, every positive style
Recall@5 ≥0.85, merge Recall@5 =1, zero forbidden families, zero unrelated nonempty results, real
p95 ≤25 ms and synthetic p95 ≤150 ms. Survivors SHALL maximize MRR@5, then Recall@1, higher floor,
lower weight. Budget-abstained positives SHALL count as misses, not disappear from denominators.
IF no configuration qualifies, THEN THE SYSTEM SHALL publish FAIL and leave v2 active without
expanding the grid, relaxing a limit/gate or choosing the closest result.

### IBR-R11 — Prove bounded scoring against an exact oracle

WHEN verifying the scorer, THE SYSTEM SHALL compare uncapped direct-accumulation scores/ranks with
a small brute-force mathematical oracle, test whole-token noise and complete-identity admission,
unseen grams, duplicate forms, stable ties and budget aborts, and report work counts on both corpora.
It SHALL measure optimization before/after without rewriting v3's report or pretending changed
normalization makes v3/v4 scores identical.

### IBR-R12 — Disclose cost and guard against cheap abstention claims

WHEN cost is measured, THE SYSTEM SHALL disclose host/Python, K, warm-ups, raw samples, percentile
method, query IDs, document/form/posting counts and work limits. It SHALL measure all 199 real dev
queries and the design's 120-query synthetic scale workload. All 60 exact and 20 contextual synthetic
identity targets SHALL be found at K=5, and at least 17/20 synthetic single-edit targets SHALL be
found; otherwise the scale smoke SHALL FAIL regardless of latency. The original 20 dev-query scale
workload SHALL also be reported separately for diagnostic comparison.

### IBR-R13 — Isolate runtime and freeze a fully evidenced artifact

WHEN a qualified configuration is frozen, THE SYSTEM SHALL use a new v4 schema/version/path with
mandatory complete selection evidence, code/protocol/corpus/development hashes, policy and budget
values. Conflicting v3/v4 opt-ins SHALL fail readiness, not choose silently. Without opt-in v2 SHALL
remain active. Missing/stale/malformed artifacts or index failures SHALL produce not-ready/503
without a fabricated identity. No active artifact SHALL be overwritten.

### IBR-R14 — Preserve canonical authority and typed debug

WHILE v4 is enabled experimentally, THE SYSTEM SHALL keep final UUID/product/confidence/status/
calibration/policy controlled solely by canonical RAG, preserve typed Human Knowledge identities and
sparse/dense/character evidence, and expose v4/policy/index/artifact/work metadata only in debug/
health. Non-debug canonical response fields SHALL remain unchanged.

### IBR-R15 — Freeze before a new independently reviewed final test

WHEN v4 qualifies, THE SYSTEM SHALL commit code/artifact before authoring 105 new output-blind
`family-retrieval-holdout-v2` questions, reject reuse of original/development/indexed questions,
and require owner approval before labels/scoring. Final gates SHALL remain positive Recall@5 ≥0.85,
Recall@1 ≥0.65, MRR@5 ≥0.75, every style Recall@5 ≥0.75, coverage ≥0.90, merge Recall@5 =1,
zero forbidden families and zero unrelated nonempty results. Final failures SHALL NOT tune v2.

### IBR-R16 — Keep expansion and deployment gated

WHEN closing the feature, THE SYSTEM SHALL authorize T49 design only after independent final
quality, regression, local/scale cost, full tests and documentation all pass. Planning or synthetic
scale SHALL NOT authorize PostgreSQL writes, real 3,000-row ingestion, default v4 deployment or a
production-accuracy/latency claim.

## Acceptance boundary

Owner approval of these requirements/design/tasks permits IBR-T1 only. Each next task follows its
upstream artifacts. The existing HRR final tasks are superseded in execution order by IBR-T4–T5,
not marked done. If v4 also fails, preserve that report and return to design; do not iterate policy
values against a viewed final set. All work stays inside `Product Variant Resolver`.
