# Representative Hard Benchmark v1 — Design

Date: 2026-09-26. Mode: Lite / Lean Industrial. Status: **OWNER-APPROVED FOR IMPLEMENTATION**.

## 1. Overview

The benchmark is a governance and evaluation system before it is a collection of rows. Current
fixture evidence is valuable for deterministic regression but is too small and saturated to answer
whether hybrid retrieval, structured evidence, confidence calibration, or a future reranker improves
difficult real inputs. At the same time, the repository already contains real-looking source rows
whose authority is deliberately limited: Human Knowledge is review evidence, local workbooks are
staging-only, and Wiki release rows are not canonical identities.

Version 1 therefore proceeds through three visibly separate layers:

```text
A. schema/tooling + source/provenance audit
                  |
                  v
       OWNER SOURCE GATE + CATALOG-TRUTH GATE
                  |
                  v
B. 60-case owner-approved pilot tranche
   20 matched | 20 ambiguous | 20 no_match
                  |
          family-safe freeze
                  |
        label-blind Test collection
                  |
          one-time label join
                  |
                  v
C. measured report + QA decision
                  |
        separate approval required
                  v
   future expansion toward 300–500 cases
```

If the source or catalog-truth Gate cannot pass, Layer A is still a useful deliverable and the work
stops honestly. The system must never manufacture 20 matched rows by treating Human Knowledge,
staging data, fuzzy alignment, or the top retrieved candidate as truth.

## 2. Core user flows

### Project owner approves a source

The owner reviews a source-inventory packet that separates access permission, content license,
retention, public redistribution, private evaluation, privacy, and exact-label suitability. The owner
approves a precise use or rejects/holds it. Approval of a local file does not authorize a new crawl;
approval for local-only evaluation does not authorize committing raw titles to Git.

### Reviewer labels a case

The reviewer sees the source evidence and independently reviewed catalog-authority evidence, not the
resolver's suggested winner. They choose `matched`, `ambiguous`, `no_match`, or `held`. A matched
choice is impossible unless an existing canonical UUID has a valid exact-variant authority record.
Held rows remain in the review inventory but never enter scored denominators.

### Evaluator measures the frozen resolver

Development cases may be inspected for tooling checks and future decisions. For formal Test, the
collector loads only queries and frozen runtime/catalog configuration, runs the resolver/ablation
arms, and writes label-blind raw results. A separate scorer verifies all hashes, then joins labels and
produces case-level and aggregate evidence. The scorer cannot rerun retrieval or change a threshold.

### Interviewer inspects evidence

The public report states exact sample sizes, source/publication limits, matched denominators, catalog
scope, failure breakdown, and exploratory calibration limitations. Engineering reproducibility and
resolver quality receive separate verdicts; a poor result is published rather than tuned away.

## 3. System architecture

```text
existing local assets / future authorized export
                    |
            source inventory builder
                    |
          provenance + publication Gate
                    |
        review candidate / held inventory
                    |
        exact canonical authority validator
                    |
        output-blind owner label workflow
                    |
    group-aware deterministic split + manifests
              /                     \
    Development                  sealed Test
         |                           |
 tooling checks only          label-blind collector
                                     |
                          immutable raw candidates
                                     |
                             one-time scorer
                                     |
               JSON + Markdown + SVG/table evidence
                                     |
                    QA / AI eval / Project Log
```

The new evaluator is an offline experimental surface. It may call existing retrieval components but
must not modify FastAPI, runtime defaults, canonical tables, Human Knowledge indexes, or calibration
artifacts.

## 4. Frontend/backend boundaries

There is no application UI change in this milestone. Backend/tooling owns strict schemas,
validators, deterministic builders, label-blind collection, scoring, metrics, and reports. QA and
documentation own owner-review packets, provenance decisions, label review, source/public safety,
requirement mapping, AI eval, evidence, and Project Log. The existing debug UI and `/resolve` API are
read-only systems under test, not implementation targets.

## 5. Tech stack assumptions

- Python and strict JSON artifacts remain the deterministic implementation baseline.
- Existing resolver modules provide sparse, hashing-based similarity, structured retrieval, RRF,
  heuristic reranker, logistic confidence, and policy outputs.
- SHA-256 manifests bind every source and derived artifact.
- Markdown reports and repository-native SVG or tabular plots remain inspectable without a notebook.
- Owner-only evidence may remain outside Git; public manifests store only approved metadata,
  non-reversible digests, and aggregates.
- No network library, Selenium/browser driver, LLM labeling service, new embedding model, or neural
  dependency is needed for this milestone.

## 6. Data model

### 6.1 `SourceInventoryEntry`

```text
source_id
source_kind                    synthetic_fixture | owner_scan | owner_export |
                               licensed_text_derivative | authorized_export | other
origin_reference
acquisition_method
local_sha256                   nullable when no local artifact exists
access_permission_status       approved | blocked | unknown | not_applicable
content_license_status         approved | blocked | unknown
retention_scope                prohibited | local_only | public
redistribution_scope           prohibited | aggregate_only | public_rows
privacy_review_status          approved | blocked | pending
benchmark_uses                 query_provenance | family_context | exact_variant_authority |
                               negative_control | none
evidence_refs[]
owner_decision                 approved | rejected | pending
owner_decision_metadata
```

`benchmark_uses` is allowlisted per source. One approved use never implies another.

### 6.2 `CanonicalAuthorityRecord`

```text
authority_id
canonical_uuid
canonical_catalog_version
catalog_record_sha256
variant_fields_verified[]      casting, release_year, series, color, collector_number,
                               series_position, edition, identifiers as available
independent_evidence_refs[]
evidence_source_ids[]
resolver_output_consulted      must be false for label establishment
reviewed_by
reviewed_at
review_reason
status                         approved_exact | insufficient | conflicted | revoked
```

Only `approved_exact` can support a matched label. Family-only evidence never becomes this record.
Synthetic fixture authority can remain valid for regression but is explicitly ineligible for the
representative pilot's non-synthetic quota.

### 6.3 `BenchmarkQuery`

```text
case_id
query
source_id
source_record_ref              opaque/local-safe reference when needed
public_safe
family_group_key
evidence_event_group_key       groups duplicate/alias observations
challenge_tags[]
authored_by
authored_at
resolver_output_viewed         false before freeze
split                          development | test
```

The query artifact deliberately contains no expected status, UUID, correctness flag, or target rank.

### 6.4 `BenchmarkLabel`

```text
case_id
expected_status                matched | ambiguous | no_match
expected_canonical_uuid        required only for matched
canonical_authority_id         required only for matched
family_label                   human-readable, non-authoritative context
failure_type                   controlled primary taxonomy
hard_negative                  boolean
hard_negative_kind             same_casting_different_release | other | null
source_id
evidence_refs[]
review_status                  approved | held | rejected
reviewed_by
reviewed_at
review_reason
public_safe
```

Held/rejected records are not copied into the scored benchmark. `family_label` exists to enforce
family-safe grouping and support analysis; it cannot identify a canonical variant by itself.

### 6.5 `BenchmarkManifest`

The manifest freezes schema/dataset versions; inventory, query, label, authority, catalog and config
checksums; exact counts by status/source/split/failure type; group membership; leakage assertions;
public/private scope; author/reviewer declarations; model/index versions; and allowed/deferred uses.

### 6.6 `LabelBlindRawResult`

Each Test result stores the query ID, parsed signals, ordered candidates through K=50 when available,
canonical UUIDs, per-source ranks/scores, RRF/reranker ranks, calibrated probability, policy status,
returned UUID, timings, errors, and runtime/config hashes. It contains no expected label, target rank,
correctness, metric, quality gate, or winner.

### 6.7 `ScoredResult`

The scorer appends expected status/UUID, target ranks per arm, decision correctness, failure category,
calibration target, and raw numerator contributions. Aggregate metrics must be recomputable from the
ordered case list.

## 7. Source and authority Gates

### Gate A — Inventory/provenance readiness

The current repository can be inventoried without external access:

| Source | Current known state | Allowed starting use |
|---|---|---|
| `fixture-v1` benchmark/catalog | CC0 synthetic/curated, 100 cases/120 products | regression/tooling only |
| 101 real noisy scans | local human labels; 0 canonical, 2 family-only, 99 unmapped | audit only until owner confirms rights/use |
| 1,763 owner workbook rows | local, review-only, no canonical links, redistribution unknown | provenance/review inventory only |
| 100 checked-in Wiki rows | attributed CC-BY-SA text derivative, held outside evaluation/canonical truth | family/release question source only |
| live marketplaces/Fandom | no current benchmark authorization | blocked |

Gate A passes when all source-use cells are explicit and checksum-bound. It does not authorize case
publication or establish any exact variant truth.

### Gate B — Owner source decision

The owner must approve each exact source/use/publication combination. Potential options are an
authorized owner export, manually supplied titles with documented reuse rights, or another source
with explicit bulk/API/data terms. The spec does not choose on the owner's behalf. If only local-only
use is approved, raw artifacts stay untracked and only safe manifests/aggregates may be published.

### Gate C — Catalog-ground-truth eligibility

Before any matched label, the referenced canonical UUID must already exist in the frozen catalog and
have an independent exact authority record. Creating/promoting real canonical variants is outside
this benchmark milestone and requires its own reviewed catalog process. With the current state of
zero real exact mappings, Gate C is expected to block matched pilot completion until that upstream
authority exists.

### Gate D — Pilot composition and freeze

Exactly 60 non-synthetic approved cases are required: 20/20/20 status balance, the hard-negative
floor, failure-type coverage, no duplicate evidence events, family-safe split, and public/private
scope validation. A partial set remains a labeled pilot draft, never a representative benchmark.

## 8. Split and leakage design

The split unit is a connected group, not a row. Cases are joined when they share a normalized casting
family, canonical family membership, source evidence event, listing duplicate, or alias relationship.
All members of a connected component receive the same split. A deterministic seeded group allocator
targets roughly 20 Development / 40 Test while preserving 20/20/20 status balance and challenge
coverage as closely as the group constraint permits; exact achieved counts are reported rather than
forcing row leakage.

Development may be used only after its labels are frozen. Test query text may be loaded by the
collector, but Test labels remain a separate artifact. The formal lifecycle is:

```text
freeze sources/catalog/config/query pack/labels/split
  -> commit or checksum checkpoint
  -> collect Test raw without labels
  -> freeze raw + manifest
  -> one-time score against labels
  -> publish; mark Test development-known
```

Changing the query, group, label, catalog, retriever, calibration, threshold, or configuration after
freeze creates a new benchmark/run version rather than overwriting v1.

## 9. Evaluation contracts

### Candidate generation

For RHB-R5-eligible matched cases:

- Recall@K = matched cases whose exact UUID appears by K / all eligible matched cases, for
  K=`5,10,25,50`;
- empty-candidate rate = cases with zero candidates / all scored cases.

The report also gives raw target ranks and counts. Candidate generation is evaluated before any
reranker and never conditions on “target was retrieved.”

### Ranking

- Top-1 accuracy uses all eligible matched cases, including retrieval misses as incorrect.
- MRR@10 assigns zero to a miss or rank greater than 10.
- NDCG@10 uses one binary relevant exact UUID per matched query; a miss is zero.
- hard-negative accuracy is Top-1 over the declared same-casting/different-release subset.

### Resolver decisions

For returned `matched` results, precision is correct exact matches divided by all predicted matches.
Coverage is correctly matched gold cases divided by all expected matched cases. False-match rate is
predicted matches on expected ambiguous/no-match cases divided by all expected ambiguous/no-match
cases. Abstention includes `ambiguous` and `no_match`. Wrong-identity matches, under-abstention and
over-abstention remain separate raw counts.

Risk/coverage sweeps are offline analyses over predeclared thresholds and cannot rewrite the frozen
runtime policy. For a threshold, coverage is attempted exact matches / all scored cases; risk is
incorrect attempted exact matches / attempted exact matches. Precision is `1-risk` when denominators
match. Every point retains its raw numerator/denominator.

### Calibration

Let `p` be the frozen calibrated probability attached to the proposed top canonical identity and
`y=1` only when that exact identity equals an RHB-R5-approved UUID; otherwise `y=0`. Report mean
`(p-y)^2` as Brier score. ECE uses fixed bins `[0,.1), ... [.9,1]` and weights the absolute difference
between mean confidence and empirical correctness by bin count. Empty bins stay visible. The
reliability plot is a view of the table, not a separate source of truth.

Because the pilot is small, calibration outputs are diagnostic and carry no production claim.
Logistic refitting or Isotonic Regression is deferred until a larger Development set exists; Test
labels can never fit either method.

### Retrieval ablation

The evaluator derives eight arms from existing signals. Combination arms fuse only participating
rankers using the same RRF constant/configuration. Structured-only must expose its own ordered
candidates; if the current interface cannot do that without changing production behavior, the arm is
reported `not_available` until a read-only experiment adapter exists. No arm changes `/resolve`.

## 10. API and artifact interfaces

No HTTP API changes are allowed. Proposed offline commands are contracts, not implementation in this
planning turn:

```bash
python -m product_variant_resolver.representative_benchmark inventory --check
python -m product_variant_resolver.representative_benchmark validate
python -m product_variant_resolver.representative_benchmark collect-test
python -m product_variant_resolver.representative_benchmark score-test
python -m product_variant_resolver.representative_benchmark report --check
```

Proposed versioned paths:

```text
data/evaluation/representative-hard-benchmark-v1/
  source-inventory.json
  source-inventory-manifest.json
  canonical-authority.json
  query-pack.json
  labels.json
  benchmark-manifest.json

reports/representative-hard-benchmark-v1/
  test-raw.json
  test-raw-manifest.json
  evaluation.json
  evaluation.md
  precision-coverage.svg
  risk-coverage.svg
  reliability.svg
  retrieval-ablation.svg
```

If rights require local-only data, the raw query/label files use a documented ignored local path and
the repository contains only a non-reversible manifest plus public-safe aggregate report. The
validator must prevent a report whose omitted private fields make metrics non-recomputable within the
authorized review environment.

## 11. Error handling

- Missing permission, unresolved redistribution, privacy risk, or pending owner decision blocks the
  affected source/use.
- A matched row without a valid existing canonical UUID and approved authority record fails closed.
- A held row, family-only label, Human Knowledge UUID, staged-row identifier, or guessed candidate
  cannot enter scored matched data.
- Duplicate queries/evidence events, cross-split family leakage, status/count imbalance, inadequate
  challenge coverage, stale hashes, label fields inside Test raw, or labels loaded during collection
  fail before output replacement.
- A valid model-quality failure still writes a complete report; engineering success never converts
  it into a quality PASS.
- Zero denominators produce `not_applicable` with raw counts, never a fabricated `0` or `1`.
- Interrupted writes use temporary files and atomic replacement; prior frozen artifacts remain intact.

## 12. Basic security, privacy, and licensing notes

The default workflow is offline. No credential is required or stored. External text is untrusted and
must be treated as data in reports, never executable markup. Public artifacts remove usernames,
contact details, order IDs, or other personal information and retain required attribution. Source
licenses and platform access terms are independent Gates. Review records use a stable reviewer label,
not private account data. Local-only evidence paths, if any, stay ignored and are represented publicly
only by approved metadata and SHA-256 digests.

## 13. Testing strategy

- **Schema/validator unit tests:** every required field, enum, cross-field rule, unknown-field reject,
  matched-authority constraint, held exclusion, public/private rule, duplicate and checksum mutation.
- **Provenance tests:** blocked/unknown permission, local-only redistribution, unauthorized source,
  PII field, missing attribution, and network-client import all fail as declared.
- **Split/leakage tests:** connected family/evidence groups never cross splits; deterministic repeat;
  changed seed/version is visible; Test labels are not imported by collection code.
- **Metric tests:** hand-computed Recall@K, Top-1, MRR, NDCG, precision, coverage, false-match,
  abstention, risk/coverage, ECE, Brier, bins, zero denominators, failure taxonomy, and unavailable
  ablation arms.
- **Integration tests:** collect label-blind raw from frozen local fixtures, verify candidate parity
  across comparable arms, score without reretrieval, generate deterministic JSON/Markdown/SVG, and
  preserve prior artifacts after tampering.
- **Regression:** existing fixture evaluation, canonical service/API, Human Knowledge authority
  boundary, release staging isolation, full pytest, Ruff, strict MyPy, compileall, link/hash checks,
  and `git diff --check`.
- **QA closure:** requirement-to-test evidence, exact denominators, source/publication review, AI-eval
  rubric, Project Log, and separate engineering/model-quality verdicts.

## 14. Architecture decisions and trade-offs

### Use a 60-case pilot before 300–500

Sixty cases keep manual evidence review feasible while forcing balanced decision outcomes and a real
same-casting release challenge. It is not enough for production or statistical claims. Expanding
immediately to 300–500 would multiply labeling mistakes before schema, authority, leakage and metric
contracts are proven.

### Require existing independent canonical truth for matched labels

This may block the project because the 101 current real noisy scans have zero exact canonical
alignments. That is preferable to circular evaluation where the resolver's own nearest candidate
becomes its answer key. Canonical expansion, if needed, is an upstream product-data milestone rather
than a hidden benchmark side effect.

### Keep fixture data as regression, not representation

The 100-case fixture remains useful for deterministic CI and backward compatibility. Mixing it into
the 60-case representative denominator would make the result easier without increasing real evidence,
so it is excluded from the pilot quota and reported separately.

### Publish a null or failed result

The benchmark's job is to expose weaknesses. It has an engineering/data-quality Gate, not a
preselected resolver-accuracy PASS threshold. Observed quality is published with exact denominators;
future promotion thresholds may be set using Development data and verified on a fresh Test holdout.

## 15. Deferred work

- Source acquisition or canonical catalog expansion required to clear Gates B/C.
- Expansion from 60 to 300–500 reviewed cases.
- Calibration refitting/Isotonic Regression after adequate Development data.
- Runtime, threshold, retriever, embedding, reranker, Pointwise, or Listwise changes.
- Large-catalog 10K/100K/1M performance and PostgreSQL ANN/concurrency experiments.
- Statistical confidence intervals or production SLAs beyond the pilot's defensible scope.
