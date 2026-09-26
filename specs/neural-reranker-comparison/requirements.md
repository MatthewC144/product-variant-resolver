# Neural reranker architecture comparison v1 — Requirements

Date: 2026-09-25. Mode: Lite / Lean Industrial. Status: **COMPLETE — formal result `winner: null`; RRF remains runtime default**.

## Goal

Complete the original portfolio milestone that compares the canonical resolver's unchanged RRF
ranking with a neural pointwise cross-encoder and a neural listwise reranker. All three arms must
receive the same frozen candidate pool so that measured differences come from reranking rather than
retrieval changes. The experiment tests the bounded hypothesis that listwise context may help when
near-duplicate variants differ by year, color, series, or collector number; it does not assume that
listwise must win.

This milestone is a ranking experiment on the committed `fixture-v1` canonical benchmark. It does
not reopen Human Knowledge identity admission, promote review-only data, change confidence
calibration, or activate a new runtime ranker. Its result may legitimately be `winner: null`, in
which case RRF remains the default and the negative result is published.

## Requirements

### NRC-R1 — Canonical ranking boundary

WHEN the comparison is prepared, THE SYSTEM SHALL operate only on candidates produced by the
canonical catalog retrieval pipeline for the committed `fixture-v1` benchmark. Human Knowledge
RAG documents, review-family projections, HICS artifacts, release staging rows, and private shadow
evidence SHALL NOT become ranking candidates, labels, model features, or canonical answers.

### NRC-R2 — Benchmark and split integrity

WHEN benchmark data is loaded, THE SYSTEM SHALL verify the committed dataset version, catalog
version or checksum, unique case IDs, immutable canonical UUID targets, and casting-family-disjoint
train/dev/test assignments. The current denominators SHALL be reported exactly: 100 total cases,
58 train, 21 dev, and 21 test; each split's matched, ambiguous, no-match, and hard-negative counts
SHALL also be preserved. A casting family SHALL NOT occur in more than one split.

### NRC-R3 — One label-blind frozen candidate pool

WHEN candidate pools are built, THE SYSTEM SHALL run the unchanged sparse, dense, structured, and
RRF retrieval path once per benchmark case with candidate depth at most 25, before any neural
scoring. It SHALL freeze each candidate's canonical identity, searchable fields, source ranks,
structured matches/conflicts, RRF rank/score, timings, and source checksums without expected labels,
winner fields, or neural scores. All three experiment arms SHALL consume byte-identical candidates
for each case; no arm may retrieve, add, delete, or substitute a candidate.

### NRC-R4 — Three explicit comparison arms

WHEN the experiment is scored, THE SYSTEM SHALL compare exactly these arms: `rrf` (no reranker and
the frozen RRF order), `neural_pointwise` (a local pointwise cross-encoder), and
`neural_listwise` (a local reranker that uses candidate-set context). The report SHALL NOT describe
the existing token-overlap `heuristic-v1` reranker as neural, pointwise cross-encoder evidence, or
listwise evidence.

### NRC-R5 — Pointwise independence

WHEN `neural_pointwise` scores a candidate, THE SYSTEM SHALL compute its score from the query and
that candidate's allowed representation without reading the other candidates' text, rank position,
neural scores, or identities. Reordering or batching the same candidate pairs SHALL NOT change their
scores beyond a declared numerical tolerance. The final order SHALL use a deterministic tie-break.

### NRC-R6 — Genuine listwise context

WHEN `neural_listwise` scores a case, THE SYSTEM SHALL receive the query and the complete bounded
candidate list together and SHALL model candidate-relative evidence rather than calling the
pointwise scorer independently under a different name. Candidate input order SHALL NOT determine
the semantic result: a declared permutation-equivariance test SHALL restore the same per-candidate
scores and ranking after mapping identities back. Padding or truncation SHALL be deterministic and
may not exceed the frozen candidate depth.

### NRC-R7 — Allowed evidence and leakage prohibition

WHEN either neural model is fitted or scored, THE SYSTEM MAY use normalized query/candidate text,
generic extracted year, color, series, collector-number and quantity signals, structured
match/conflict indicators, and frozen retrieval ranks/scores. It SHALL NOT use case ID, split name,
expected status, expected UUID/canonical ID, label notes, dataset row order, UUID lexical order,
test metrics, Human Knowledge decisions, or private outcomes as predictive features. Ground-truth
identity MAY be joined only by the training/evaluation layer to construct labels and metrics.

### NRC-R8 — Train/dev/test lifecycle

WHEN models are trained, THE SYSTEM SHALL fit weights only on matched train families and SHALL use
dev families only for bounded hyperparameter/configuration selection and early stopping. One frozen
configuration per neural architecture SHALL be selected before test scoring. Test labels SHALL NOT
be loaded by fitting or configuration-selection code. The three frozen arms SHALL be evaluated on
test exactly once for v1; after test results exist, source/model changes require a new explicitly
versioned experiment rather than overwriting or rerunning v1.

### NRC-R9 — Retrieval misses remain visible

WHEN a matched target is absent from its frozen candidate pool, THE SYSTEM SHALL retain `rank=null`
for every arm, count the case as a retrieval miss, and forbid either reranker from synthesizing the
target. Candidate-pool Recall@10/25 SHALL be reported once and SHALL be identical across the three
arms. Reranking claims SHALL distinguish retrieval recall from ordering quality.

### NRC-R10 — Reproducible local model artifacts

WHEN a neural configuration is frozen, THE SYSTEM SHALL record architecture name, model/provider
version, training seed, numeric precision, feature/input schema, preprocessing version, dependency
versions, license, artifact checksum, training split checksum, selected hyperparameters, and CPU
reference environment. Training and evaluation SHALL make no paid or remote inference call. Any
pretrained artifact SHALL be present locally and checksum-validated before the frozen experiment.

### NRC-R11 — Required metrics and paired evidence

WHEN dev or test results are produced, THE SYSTEM SHALL report Top-1 accuracy, MRR@10,
hard-negative accuracy, candidate Recall@10/25, and warmed p50/p95 reranking latency for every arm.
It SHALL publish raw numerators/denominators, per-case baseline-to-model rank changes, and results by
declared `failure_category`. Ambiguous and no-match cases MAY be reported as score diagnostics but
SHALL NOT be relabeled as positive ranking targets or mixed into matched-case Top-1 denominators.

### NRC-R12 — Predeclared value and latency gate

WHEN final test evidence is evaluated, a neural arm SHALL qualify as a recommendation only if it
improves Top-1 accuracy by at least `0.05` absolute over RRF, does not reduce hard-negative accuracy,
does not reduce MRR@10, preserves the identical Recall@25, and keeps warmed end-to-end resolver p95
latency at or below the existing `1.5 s` CPU smoke budget. Because the frozen test has only 12
matched cases, the report SHALL state that one case changes Top-1 by about `0.0833`, show paired case
transitions, and avoid claims of production accuracy or statistical generality.

### NRC-R13 — Deterministic recommendation and null result

WHEN more than one neural arm passes NRC-R12, THE SYSTEM SHALL choose by the predeclared order:
higher hard-negative accuracy, then higher Top-1 accuracy, then higher MRR@10, then lower p95
reranking latency, then the simpler deployment profile. IF no neural arm passes every gate, THEN THE
SYSTEM SHALL persist `winner: null`, retain RRF as the default, identify each failed gate, and treat
the negative result as a completed experiment rather than retuning against test.

### NRC-R14 — Artifact integrity and phased commands

WHEN the v1 experiment is executed, THE SYSTEM SHALL separate and checksum-bind these phases:
protocol/candidate-pool freeze, train/dev model selection, one-time label-blind test collection, and
label-joined scoring/reporting. Existing valid artifacts SHALL validate as `unchanged`; partial
state, unexpected files, checksum drift, schema drift, invalid numerics, duplicated identities,
candidate-order mismatch, or source drift SHALL fail closed without overwrite or implicit rerun.

### NRC-R15 — Inspectable ranking output

WHEN a case is inspected, THE SYSTEM SHALL expose the query, expected target only in scored output,
shared candidate identities, RRF/source ranks and scores, pointwise score/rank, listwise score/rank,
structured matches/conflicts, changed-rank direction, latency, model/artifact versions, and a bounded
reason describing the evidence available to each architecture. The output SHALL distinguish model
score from calibrated match probability.

### NRC-R16 — Runtime and Dual-RAG safety gate

WHEN the comparison completes, THE SYSTEM SHALL NOT automatically change `PVR_RERANKER_ENABLED`,
the FastAPI contract, confidence calibration, decision thresholds, PostgreSQL, canonical catalog,
Human Knowledge RAG, review-family state, or release promotion. Even a passing recommendation
requires a separate opt-in Dual-RAG runtime integration specification and API/regression QA.

### NRC-R17 — Portfolio-quality reporting without inflated claims

WHEN v1 closes, THE SYSTEM SHALL create machine-readable and Markdown reports plus a README results
table comparing RRF, neural pointwise, and neural listwise. Documentation SHALL name the dataset as
a 100-case synthetic/curated fixture benchmark, show the 12 matched-test denominator, identify the
model and hardware, explain whether listwise helped near-duplicate cases, and use measured values
only. If the result is null or tied, the README SHALL say so plainly and SHALL NOT invent an
improvement percentage for a resume bullet.

## Out of scope

- Retuning, replacing, or creating an HICS-v5 Human Knowledge identity-admission policy.
- Adding held review families or the 1,763 release-staging rows to canonical ground truth.
- Changing sparse, dense, structured, RRF, candidate-depth, calibration, or abstention behavior in
  the comparison itself.
- Fine-tuning on test labels, repeated test runs after model changes, or selecting only favorable
  failure categories.
- Paid inference APIs, runtime network inference, GPU-only deployment, or an open-ended model-zoo
  benchmark.
- Claiming that the 100-case fixture establishes real marketplace coverage or production accuracy.
- Automatic runtime activation, API changes, PostgreSQL writes, color completion, or variant
  promotion.

## Evidence motivating this milestone

The original project brief names pointwise versus listwise reranking as a core experiment and asks
whether candidate-relative context improves near-duplicate variant collisions. The implemented MVP
currently has hybrid retrieval and RRF plus a deterministic `heuristic-v1` token-overlap ablation;
that heuristic produced `0.0` absolute Top-1 gain over RRF and is disabled by default. It is not a
neural cross-encoder and cannot answer the original architecture question.

The committed fixture is suitable for a bounded engineering demonstration: it has 120 canonical
variants and 100 grouped benchmark cases, including 60 matched examples and 20 each ambiguous and
no-match. Its final test partition is small—21 total and 12 matched—so this specification emphasizes
paired cases, exact denominators, failure categories, reproducibility, and honest null-result
handling rather than a broad accuracy claim.

## Owner confirmation checkpoint

The owner confirmed these requirements on 2026-09-24. That confirmation authorizes the Lite design
step only. It does not yet authorize dependency installation, model acquisition, training, test
scoring, runtime activation, or API changes. Those actions remain behind confirmed `design.md` and
`tasks.md` documents.
