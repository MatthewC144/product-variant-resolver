# Human Knowledge Retriever Redesign — Requirements

> Mode: Lite / Lean Industrial
>
> Phase: Specification
>
> Status: Proposed; awaiting project-owner confirmation before implementation
>
> Proposed retriever: `human-knowledge-hybrid-v3`

## Purpose

Improve typo, abbreviation, punctuation, spacing, and numeric-form retrieval in the second,
debug-only Human Knowledge RAG without tuning against the now-known
`family-retrieval-holdout-v1`, weakening its failed gate, changing canonical resolution, or
starting PostgreSQL/3,000-row expansion before a new unseen evaluation passes.

## Functional requirements

### HRR-R1 — Preserve v1 as immutable historical evidence

WHILE the retriever is redesigned, THE SYSTEM SHALL NOT change or use v1 queries, labels, ranks,
metrics, thresholds, or failed-case outcomes for fitting, configuration selection, or final v3
quality claims; v1 MAY be cited only as the diagnostic reason for starting this feature.

### HRR-R2 — Freeze a development-only challenge set

WHEN development data is prepared, THE SYSTEM SHALL create `family-retrieval-development-v1` with
exactly 199 `dev` cases: 168 positives covering each of 42 accepted families in four declared
transformation styles, 4 merge controls, 7 hold controls, and 20 unrelated controls split evenly
between opaque zero-overlap text and generic marketplace text with no resolvable identity.

### HRR-R3 — Disclose development-data leakage

WHEN the development set is published, THE SYSTEM SHALL label its family transformations as
derived from indexed identities, allow it only for implementation/configuration selection, exclude
it from final accuracy claims, and record deterministic source/output checksums and case counts.

### HRR-R4 — Restrict character-search identity fields

WHEN character features are indexed, THE SYSTEM SHALL use only `casting` and approved `aliases` for
review-family documents and only `casting` plus `human_label_names` for provisional-variant
documents; it SHALL NOT index decision reasons, URLs, source IDs, held releases, private text,
pricing keywords, series labels, initial recognition text, or canonical-only attributes.

### HRR-R5 — Add deterministic character-level candidate generation

WHEN v3 builds the Human Knowledge index, THE SYSTEM SHALL create a versioned, dependency-free
character n-gram TF-IDF index over normalized spaced and compact identity forms, use an inverted
posting map rather than an unconditional full scan, and resolve equal scores by stable knowledge
UUID.

### HRR-R6 — Remove shared-token dependence without removing safety floors

WHEN a query has no exact token overlap, THE SYSTEM SHALL still permit a document to enter the
candidate union through character similarity above the selected development threshold; a query
with neither token overlap nor sufficient character evidence SHALL return no Human Knowledge
candidate.

### HRR-R7 — Preserve the three-source hybrid contract

WHEN v3 ranks Human Knowledge, THE SYSTEM SHALL union exact-token and character candidates, compute
existing `hashing-v1` dense scores only over that bounded union, and fuse available sparse, dense,
and character ranks with deterministic weighted RRF at `k=60`; missing source ranks SHALL
contribute zero rather than a fabricated rank.

### HRR-R8 — Precommit the finite configuration search

WHEN development selection runs, THE SYSTEM SHALL evaluate only character score floors
`0.25–0.55` in increments of `0.05` and character RRF weights `0.5`, `1.0`, and `1.5`, while keeping
the sparse/dense weights, dense dimensions, RRF constant, and K=5 fixed.

### HRR-R9 — Select configuration by a deterministic safety-first rule

WHEN candidate configurations are compared, THE SYSTEM SHALL first reject any configuration with a
forbidden-family hit, unrelated non-empty result, merge Recall@5 below `1.0`, positive Recall@5
below `0.90`, or any positive style Recall@5 below `0.85`; among survivors it SHALL maximize MRR@5,
then Recall@1, then prefer the higher character floor and lower character weight.

### HRR-R10 — Fail closed when no development configuration qualifies

IF no predeclared configuration passes every development constraint, THEN THE SYSTEM SHALL publish
an explicit selection FAIL, leave v2 active, and require a new design decision rather than widening
the grid, lowering gates, or choosing the closest result after viewing output.

### HRR-R11 — Freeze the selected v3 artifact and implementation

WHEN a configuration qualifies, THE SYSTEM SHALL write a checksum-frozen selection artifact
containing corpus/development/source hashes, complete candidate metrics, the deterministic winner,
and version `human-knowledge-hybrid-v3`; v3 SHALL NOT become evaluation-eligible until this artifact
and its source implementation are committed.

### HRR-R12 — Expose traceable debug evidence without changing canonical output

WHEN debug output contains a v3 Human Knowledge candidate, THE SYSTEM SHALL expose optional
`character_rank` and `character_score` alongside sparse/dense/RRF evidence and publish the v3/index
version in health/debug metadata; requests without debug SHALL still omit all Human Knowledge
internals.

### HRR-R13 — Maintain Dual RAG isolation

WHILE v3 is enabled, THE SYSTEM SHALL keep the canonical RAG as the only source of final UUID,
status, confidence, product, calibration, and policy decisions; character-ranked family or
provisional evidence SHALL remain incapable of creating a canonical match.

### HRR-R14 — Preserve merge, hold, unrelated, and failure safety

WHEN v3 is tested, THE SYSTEM SHALL retain existing merge-to-provisional behavior, never materialize
or return forbidden family identities, return no candidates for unrelated controls, bound K to
`1–25`, reject invalid/stale selection artifacts, and map index/provider failures to not-ready/503
without fabricating identity.

### HRR-R15 — Bound local and future-scale cost

WHEN v3 is verified, THE SYSTEM SHALL report index document/posting counts and warmed single-process
p50/p95 for the 142-document corpus, require p95 `<=25 ms` at K=5 on the recorded host, and run a
clearly labeled synthetic 3,000-document scalability smoke with p95 `<=150 ms`; neither result SHALL
be called PostgreSQL, concurrent, network, or production performance.

### HRR-R16 — Freeze v3 before authoring the final holdout

WHEN v3 development selection is complete, THE SYSTEM SHALL commit its code, field contract,
configuration artifact, source/corpus checksums, and API version before any v2 holdout query is
authored or any v3 retrieval output is used during final-query review.

### HRR-R17 — Create a new output-blind final holdout

WHEN final evaluation data is authored, THE SYSTEM SHALL create
`family-retrieval-holdout-v2` with 105 new test-only cases using the same 84/4/7/10 and two-style
family coverage as v1, reject text equal to or normalized-equivalent to v1/development/indexed
queries, require `retriever_output_viewed=false`, and require separate project-owner approval.

### HRR-R18 — Retain the original final quality gate

WHEN v3 is scored on the approved v2 holdout, THE SYSTEM SHALL require positive Recall@5 `>=0.85`,
Recall@1 `>=0.65`, MRR@5 `>=0.75`, each positive style Recall@5 `>=0.75`, family coverage@5
`>=0.90`, merge Recall@5 `=1.0`, zero forbidden-family hits, and zero unrelated non-empty results;
it SHALL NOT tune or select thresholds from v2.

### HRR-R19 — Publish honest evaluation and AI evidence

IF any v2 quality, safety, regression, or reproducibility gate fails, THEN THE SYSTEM SHALL retain
v3 as experimental/debug-only or revert active debug selection to v2, publish per-case errors and an
AI-eval FAIL, and require another development/evaluation cycle rather than modifying v2.

### HRR-R20 — Guard T49 explicitly

WHEN the redesign closes, THE SYSTEM SHALL authorize T49 PostgreSQL/pgvector persistence and the
approximately 3,000-row expansion only if v2 holdout quality, canonical/T47 regression, local cost,
complete tests, deterministic data chain, and documentation gates all pass.

## Acceptance boundary

A feature PASS means v3 is a better measured second-RAG retrieval source and T49 may begin design.
It still does not authorize Human Knowledge to produce canonical identity, establish release-level
variant correctness, claim live marketplace accuracy, or claim production/SQL latency.

A development-selection FAIL or final-holdout FAIL is a valid outcome. It keeps T49 blocked and
must not be converted to PASS by changing the relevant data or gates after output is viewed.

## Out of scope

- Editing, relabeling, rescoring, or using `family-retrieval-holdout-v1` for selection.
- Changing the canonical catalog, canonical retrievers, calibrator, policy, or response authority.
- Scraping new live marketplace or Wiki data.
- PostgreSQL/pgvector persistence or actual 3,000-row ingestion.
- Calling deterministic character n-grams or `hashing-v1` a neural embedding model.
- Adding an external neural model in this Lite iteration; it requires its own model-artifact and
  dependency design if the deterministic candidate generator cannot qualify.
