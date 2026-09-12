# Family Retrieval Evaluation — Design

> Mode: Lite / Lean Industrial
>
> Status: Confirmed; T48.1–T48.3 implemented

## Overview

T47 proved that 42 accepted review-family documents are loaded and recoverable by their own exact
names. That smoke test cannot measure generalization because the indexed text and query text are
effectively the same. T48 creates a separate, output-blind challenge authoring and approval path,
then evaluates the already frozen Human Knowledge RAG v2 without tuning it.

The design deliberately treats a failed quality gate as evidence rather than as an implementation
bug to hide. The current sparse/feature-hashing/RRF retriever requires at least one shared normalized
token, so the four single-token families—Haulerback, Crescendo, Bogzilla, and Draftnator—are likely
to expose pure-misspelling limitations. Those failures must remain visible.

## Architecture

```text
42 accepted family identities        4 merges + 7 holds
             │                              │
             └──── output-blind authoring ──┘      10 unrelated controls
                              │                            │
                              ▼                            │
                 105-case pending query pack ◀────────────┘
                              │
                   project-owner label review
                              │
                              ▼
             frozen benchmark + checksum manifest
                              │
                  read-only evaluator (labels hidden
                    until candidates are retrieved)
                              │
                              ▼
               JSON/Markdown report + AI-eval verdict
                              │
              PASS ──► T49 design allowed
              FAIL ──► retriever redesign + new holdout
```

The query pack, owner approval, benchmark, and result report are separate artifacts. Version-control
order freezes query wording and labels before the first scored report so later edits cannot silently
improve the same test set.

## Interfaces

### Benchmark builder

```bash
python3 scripts/build_family_retrieval_benchmark.py --freeze-query-pack
python3 scripts/build_family_retrieval_benchmark.py --check-query-pack
python3 scripts/build_family_retrieval_benchmark.py
python3 scripts/build_family_retrieval_benchmark.py --check
```

Default inputs:

- `data/evaluation/family-retrieval-v1/query-pack.json`
- `data/evaluation/family-retrieval-v1/query-pack-manifest.json`
- `data/evaluation/family-retrieval-v1/owner-decisions.json`
- `data/review_family_registry.json` plus manifest
- `data/review_family_knowledge.json` plus manifest
- `data/human_backed_catalog.json` plus manifest

Default outputs:

- `data/evaluation/family-retrieval-v1/benchmark.json`
- `data/evaluation/family-retrieval-v1/benchmark-manifest.json`

The builder validates every invariant before atomic output replacement. `--check` constructs the
expected bytes in memory and never writes.

### Evaluator and report

```bash
PYTHONPATH=src python3 -m product_variant_resolver.human_knowledge_evaluation \
  --benchmark data/evaluation/family-retrieval-v1/benchmark.json \
  --output reports/family-retrieval-v1/evaluation.json

python3 scripts/generate_family_retrieval_report.py \
  --evaluation reports/family-retrieval-v1/evaluation.json \
  --output reports/family-retrieval-v1/evaluation.md
```

The evaluator must retrieve candidates before reading the expected-label branch for a case. It
returns non-zero only for invalid inputs/runtime failures; a valid evaluation that misses quality
thresholds still writes a truthful `verdict=FAIL` report.

## Data models

### Query pack

Top-level fields include schema/query-pack version, status, authoring policy, system-under-test
freeze, exact expected counts, and 105 cases. Each case contains:

- Stable `case_id`, `split=test`, and `casting_group_id`.
- `case_type`: `positive_family`, `merge_control`, `hold_control`, or `unrelated_control`.
- `challenge_style`: `marketplace_noise`, `lexical_variation`, `merge_existing_family`,
  `held_identity`, or `no_overlap`.
- Independently composed `query_text` and explicit `noise_tags`.
- `authored_by`, `authored_at`, `authoring_method`, and
  `retriever_output_viewed=false`.
- A review reference identifying the intended family/control question, but no candidate ranks,
  scores, or generated retrieval output.

Positive cases total 84: two per accepted family. `marketplace_noise` may retain recognizable
identity tokens among seller/year/series/condition noise but may not equal indexed text.
`lexical_variation` must disrupt the complete normalized casting phrase. The evaluator reports the
two styles separately so easy noisy wrappers cannot conceal spelling/abbreviation failures.

### Owner decisions

The decision artifact covers every case ID exactly once. Its discriminated label shapes are:

- Positive: expected `review_family_id` and `knowledge_type=review_family`.
- Merge control: expected existing `casting_id` and `knowledge_type=provisional_variant`, plus a
  forbidden duplicate review-family identity.
- Hold control: forbidden review-family ID/key and `expected_materialized=false`.
- Unrelated control: `expected_candidate_count=0` and proof of zero normalized token overlap.

Every decision records `decided_by=project_owner`, UTC timestamp, accepted/held decision, and reason.
The builder rejects any query edit after the owner-decision file's frozen query-pack checksum.

### Benchmark manifest

The manifest freezes query/decision/registry/catalog/projection checksums; 105/84/4/7/10 counts;
42 positive groups with two styles each; four single-token-family challenges; all test-only and
no-tuning declarations; model/index versions; allowed metrics; and exclusions from canonical,
training, persistence, and production claims.

### Evaluation result

The JSON report retains one ordered result per case: case/group/type/style, expected identity class,
returned candidate IDs/types/ranks through K=5, expected rank, and error category. Aggregate fields
include raw numerators/denominators and formula-derived metrics; the Markdown report never contains
metrics that cannot be recomputed from the JSON.

## Authoring and leakage controls

The author may read the accepted family identity question needed to compose a case but must not run
or inspect Human Knowledge retrieval until the query pack is frozen in its own commit. Query strings
cannot be copied from searchable projection text, Fandom staging/model labels, or the existing human-
label query set. An automated validator enforces exact-string and normalized equality rules, while
the project owner reviews semantic correctness and target labels.

All 105 cases are a one-time test set. There is no train or dev split because T48 performs no
selection. If the model fails, its case-level errors may inform a later redesign, but this v1 set
becomes development-known; final evidence for a changed retriever requires a newly authored v2
holdout. This prevents repeated tuning against one small benchmark.

## Metrics and gate

Primary quality metrics are positive Recall@5, Recall@1, and MRR@5. Family coverage@5 prevents a
high-volume subset from hiding families that never retrieve. Style-level Recall@5 separates noisy
wrapper robustness from lexical variation. Controls report merge-to-existing-variant Recall@5,
forbidden held/duplicate family hits, and unrelated-query non-empty results.

The precommitted PASS gate is:

| Metric | Gate |
|---|---:|
| Positive Recall@5 | `>=0.85` |
| Positive Recall@1 | `>=0.65` |
| Positive MRR@5 | `>=0.75` |
| Each positive style Recall@5 | `>=0.75` |
| Family coverage@5 | `>=0.90` |
| Merge-control Recall@5 | `=1.0` |
| Forbidden family hits | `=0` |
| Unrelated non-empty results | `=0` |

These gates are intentionally more demanding for safety controls than for noisy positive recall.
They determine only whether T49 scale experimentation is justified, not whether the resolver is
production ready.

## Error handling

- Missing, malformed, partial, duplicate, reordered, checksum-stale, or widened inputs fail before
  benchmark/report output is replaced.
- Query equality/leakage, missing style coverage, non-105 counts, unapproved labels, or authoring
  declarations inconsistent with the manifest fail closed.
- Unknown expected IDs/types or merge/hold decisions inconsistent with the T46 registry fail.
- Runtime/version mismatch refuses scoring instead of silently evaluating another index.
- A valid metric-gate failure writes a complete FAIL report and does not modify the retriever.

## Security and privacy notes

No live marketplace or Wiki request occurs during benchmark build or evaluation. Query text is
synthetic and separately authored; it must contain no account identifiers, contact details, secrets,
or private user content. JSON fields are allowlisted and rendered as text in Markdown. Source
artifacts remain local checked-in files, and evaluator outputs cannot feed runtime configuration.

## Testing strategy

- Builder tests: exact 105/84/4/7/10 composition, two cases per 42 families, four single-token
  challenges, unique IDs/queries, field allowlists, hashes, deterministic `--check`, and atomic
  preservation after invalid input.
- Leakage tests: copied/normalized exact indexed text, copied staging/human queries, viewed-output
  declarations, post-approval query edits, partial approval, and train/dev use all fail.
- Evaluator unit tests: rank/metric formulas, zero denominators, style/group coverage, all failure
  categories, threshold boundaries, and labels accessed only after retrieval.
- Integration tests: frozen v2 index, ordered raw candidates, positive/control scoring, version
  mismatch, read-only behavior, and deterministic JSON/Markdown reports.
- Regression: T47 typed API/UI tests, complete suite/data chain, canonical fixture evaluation,
  compilation, both Compose configurations, and repository-scope/whitespace checks.

## Alternatives and decision trade-offs

Reusing the 42 exact-name smoke queries was rejected because it measures document loading, not
generalization. Reusing the 100 Fandom rows was rejected because their frozen usage explicitly says
`staging_only_not_evaluation_or_canonical`. Scraping live marketplace titles during evaluation was
rejected because results are unstable, harder to license/reproduce, and can contain personal data.
Automatically generating thousands of perturbations was rejected because volume would not create
independent relevance judgments and could overrepresent easy templates.

The 105-case challenge is large enough to cover every family twice plus every known governance
control, yet small enough for project-owner review in Lite mode. The cost is wide confidence
intervals and synthetic wording; the report must disclose both.

## Deferred work

T49 may design PostgreSQL/pgvector persistence and scale measurement only after T48 produces a
truthful PASS or an explicit redesign decision. New yearly-list ingestion toward approximately
3,000 rows, neural embeddings, query expansion, and any changed retriever require separate specs
and new evaluation data.
