# Representative Hard Benchmark v1 — Requirements

Date: 2026-09-26. Mode: Lite / Lean Industrial. Status: **OWNER-APPROVED FOR IMPLEMENTATION**.

Owner confirmation: the project owner instructed the workflow to continue after reviewing the
requirements, design, task sequence, and Gate boundaries. Approval authorizes sequential task
execution only; it does not pre-approve any later source, canonical-authority, or collection Gate.

## Product goal

Create the first provenance-controlled, human-reviewed and genuinely difficult benchmark for the
canonical Product Variant Resolver. The benchmark must measure three different questions without
mixing them:

1. did retrieval place the correct catalog identity in the candidate pool;
2. did ranking order eligible candidates correctly; and
3. did the complete resolver match or abstain safely?

This milestone addresses the current evidence ceiling: the checked-in `fixture-v1` benchmark has
100 synthetic/curated cases over a 120-product fixture catalog, while its final Test split contains
21 cases and only 12 matched ranking targets. Sparse/RRF already score perfectly on that small
matched denominator, so the fixture cannot demonstrate the incremental value of harder retrieval,
structured evidence, calibration, or neural reranking.

The long-term target is a 300–500-case representative benchmark. Version 1 deliberately begins with
schema/tooling and provenance audit, then requires one owner-approved 60-case pilot tranche before
any scale expansion. It is valid for this milestone to stop at a documented Gate if no lawful source
or independently justified exact-variant truth is available.

## Observable requirements

### RHB-R1 — Source inventory before case authoring

WHEN benchmark work begins, THE SYSTEM SHALL produce a deterministic inventory of every proposed
source, including owner-supplied real noisy scans, owner-supplied release workbooks, checked-in Wiki
text derivatives, synthetic fixtures, and any newly proposed source; each entry SHALL record its
origin, acquisition method, license or permission evidence, redistribution/publication status,
privacy risk, permitted benchmark use, checksum where locally available, and unresolved conditions.

### RHB-R2 — Provenance and source-permission Gate

IF a source lacks sufficient evidence for the proposed collection, retention, evaluation, or public
redistribution use, THEN THE SYSTEM SHALL mark that use `blocked` or `local_only` and SHALL NOT copy
its content into a public benchmark. Possession of a local export, a general content license, public
page visibility, or API availability SHALL NOT by itself authorize automated collection or public
republication.

### RHB-R3 — No unauthorized collection

WHILE this milestone is active, THE SYSTEM SHALL NOT scrape, crawl, automate access to, or obtain
listing content from eBay, Mercari, Facebook Marketplace, Fandom, or any other external service
unless the project owner first supplies source-specific permission or an applicable authorized data
export and approves an exact collection manifest. The tooling SHALL perform no network collection by
default and SHALL prohibit authentication, proxy rotation, CAPTCHA bypass, browser impersonation,
or image/OCR collection.

### RHB-R4 — Explicit owner source-selection Gate

WHEN the source inventory is complete, THE PROJECT SHALL pause before case authoring until the owner
approves the exact sources, allowed fields, acquisition method, retention, publication level, and
reviewer identity for the pilot. No plan SHALL assume that eBay, Mercari, Facebook, Fandom, or the
owner-supplied local files are automatically eligible for public evaluation data.

### RHB-R5 — Catalog-ground-truth eligibility Gate

WHEN a case is labeled `matched`, THE SYSTEM SHALL require an exact canonical UUID that already
exists in the frozen canonical catalog plus an independently reviewed authority record confirming
the full release variant. That record SHALL bind the catalog version and product-record checksum,
identify evidence created independently of resolver output, cover every available variant-defining
field, name the reviewer and review time, and predate the frozen benchmark label. A nearest text
candidate, Human Knowledge result, casting-family decision, staged release row, or model suggestion
SHALL NOT establish exact canonical truth.

### RHB-R6 — Honest handling when exact variant truth is absent

IF exact canonical variant authority cannot be established, THEN THE SYSTEM SHALL NOT assign an
expected UUID or `matched` status. The item MAY be owner-reviewed as `ambiguous` or catalog-relative
`no_match` when evidence justifies that status, or SHALL remain `held` and be excluded from scored
metrics. The evaluator SHALL reject any matched case that lacks the RHB-R5 authority record.

### RHB-R7 — Canonical and Human Knowledge authority separation

WHILE benchmark cases are authored or scored, THE SYSTEM SHALL keep canonical labels independent
from Human Knowledge, review-family identities, owner release staging, and provisional variants.
Those sources MAY supply query provenance, family context, or review questions, but SHALL NOT create,
replace, or infer a canonical UUID and SHALL NOT silently enter the canonical retrieval corpus.

### RHB-R8 — Versioned human-label contract

WHEN an item is reviewed, THE SYSTEM SHALL store a versioned label record with at least `case_id`,
`query`, `expected_status`, optional independently justified `expected_canonical_uuid`,
`family_label`, `failure_type`, `hard_negative`, `hard_negative_kind`, `source_id`,
`evidence_refs`, `review_status`, `reviewed_by`, `reviewed_at`, and `review_reason`. It SHALL also
record whether the row is public-safe, local-only, held, or score-eligible and SHALL reject unknown
fields or invalid enum combinations.

### RHB-R9 — Three outcome semantics

WHEN labels are validated, THE SYSTEM SHALL define `matched` as one independently justified exact
canonical variant, `ambiguous` as multiple plausible variants or insufficient release-level evidence
to choose safely, and `no_match` as no eligible identity in the explicitly frozen catalog scope.
`no_match` SHALL NOT be presented as proof that the product does not exist outside that catalog.

### RHB-R10 — Hard-case coverage

WHEN the pilot query pack is accepted, THE SYSTEM SHALL include owner-reviewed examples of
same-casting/different-release hard negatives, aliases or abbreviations, missing metadata,
conflicting year/color/series/identifier metadata, distractor quantity or lot numbers, and products
unknown to the frozen catalog. Every case SHALL have one primary `failure_type`; additional
challenge tags MAY be recorded separately.

### RHB-R11 — Executable v1 pilot tranche

WHEN the v1 pilot becomes score-eligible, THE SYSTEM SHALL contain exactly 60 non-synthetic,
owner-approved cases: 20 `matched`, 20 `ambiguous`, and 20 `no_match`. At least 12 matched cases
across at least four casting families SHALL be same-casting/different-release hard negatives, and
each RHB-R10 challenge class SHALL have at least four cases. IF those denominators cannot be met,
THEN THE SYSTEM SHALL publish the partial tranche as a provenance or labeling artifact only and
SHALL NOT call it the representative v1 benchmark.

### RHB-R12 — Long-term scale target without quota padding

AFTER the 60-case pilot passes its data, leakage, reproducibility, and QA gates, THE PROJECT SHALL
plan separately approved expansions toward 300–500 unique human-reviewed cases. Synthetic variants,
duplicate titles, repeated snapshots, automatically perturbed copies, unreviewed labels, or multiple
rows representing the same evidence event SHALL NOT be used to satisfy the target.

### RHB-R13 — Family-safe split and leakage prevention

WHEN the pilot is split, THE SYSTEM SHALL group every related query and every canonical variant from
the same casting family into exactly one split. The split SHALL be deterministic and approximately
one-third Development and two-thirds Test while preserving status and challenge coverage where
grouping permits. Source duplicates, aliases of one listing, and near-duplicate evidence events SHALL
stay in the same group. Test labels SHALL NOT be used to fit, tune, select thresholds, rewrite
queries, choose retrievers, or select a model.

### RHB-R14 — Label-blind Test lifecycle

WHEN formal Test evaluation runs, THE SYSTEM SHALL first collect immutable candidates, ranks,
scores, calibrated confidence, policy output, timings, and configuration metadata from the frozen
Test queries without loading expected Test status or UUID. A separate one-time scoring step MAY join
the frozen raw output to frozen owner labels. After results are exposed, that Test set SHALL be
considered development-known; any materially changed resolver seeking final evidence SHALL require a
new versioned holdout.

### RHB-R15 — Candidate retrieval metrics are separate from ranking

WHEN scored matched cases are evaluated, THE SYSTEM SHALL report candidate Recall@5, Recall@10,
Recall@25, Recall@50, and empty-candidate rate independently from Top-1 accuracy, MRR@10, NDCG@10,
and same-casting/different-release hard-negative accuracy. Ranking denominators SHALL include only
matched cases whose exact canonical truth passes RHB-R5, and retrieval misses SHALL remain visible
rather than being removed from the ranking denominator.

### RHB-R16 — Resolver decision metrics

WHEN the full resolver is evaluated, THE SYSTEM SHALL report raw counts and formula-derived
precision, coverage, false-match rate, abstention rate, wrong-identity matches, under-abstention,
over-abstention, and metrics by expected status and failure type. It SHALL publish precision–coverage
and risk–coverage points over predeclared confidence thresholds without changing the frozen runtime
threshold based on Test results.

### RHB-R17 — Confidence calibration metrics

WHEN calibrated confidence is evaluated, THE SYSTEM SHALL report Expected Calibration Error with
ten predeclared equal-width bins, Brier score, and a reliability table/diagram using the binary event
“the proposed top canonical identity is the independently verified exact identity.” It SHALL retain
per-bin counts and sums so every value is recomputable. Pilot calibration SHALL be labeled
exploratory because 60 total cases are insufficient for a production calibration claim.

### RHB-R18 — Retrieval ablation

WHEN the pilot evaluator runs, THE SYSTEM SHALL compare the existing frozen retrieval signals as
read-only experiment arms: sparse only, similarity only, structured only, sparse+similarity,
sparse+structured, similarity+structured, all signals with RRF, and all signals with RRF plus the
existing heuristic reranker. The ablation SHALL use identical eligible queries/catalog/configuration,
SHALL NOT modify runtime defaults, and SHALL report unavailable arms honestly rather than simulate
results.

### RHB-R19 — Frozen artifacts and reproducibility

WHEN an inventory, query pack, label file, split, catalog snapshot, authority record, raw run, or
report is approved, THE SYSTEM SHALL freeze its schema version, content checksum, parent checksums,
counts, ordering, configuration/model/index versions, and creation/review metadata in manifests.
Re-running a completed build SHALL return byte-identical output or an explicit `unchanged`; stale,
partial, reordered, overwritten, or checksum-inconsistent inputs SHALL fail closed.

### RHB-R20 — Failure taxonomy and case-level traceability

WHEN scoring completes, THE SYSTEM SHALL retain one ordered result per eligible case and classify
failures using a controlled taxonomy including `retrieval_miss`, `variant_confusion`,
`alias_failure`, `parser_error`, `year_conflict`, `color_conflict`, `identifier_conflict`,
`unknown_product_false_match`, `under_abstention`, `over_abstention`, and
`hard_negative_failure`. Aggregate claims SHALL remain traceable to these raw case results.

### RHB-R21 — Public/private and privacy boundary

WHEN artifacts are written to the repository, THE SYSTEM SHALL include only data whose publication
is authorized, strip seller/account/contact and other personal information, and preserve required
attribution. Local-only evidence MAY be referenced by non-reversible digest and aggregate counts but
SHALL NOT be copied into Git. Missing publication rights SHALL fail public-artifact generation rather
than silently redact labels in a way that changes evaluation meaning.

### RHB-R22 — Scope and model-change boundary

WHILE this benchmark milestone is implemented, THE SYSTEM SHALL NOT retrain or rerun the neural
Pointwise/Listwise comparison, promote a new model, tune production thresholds on Test, change the
FastAPI response contract, or promote review-only rows into canonical identity. Any later model or
runtime change SHALL be a separate milestone driven by the frozen benchmark evidence.

### RHB-R23 — QA, evidence, AI eval, and Project Log

WHEN the milestone closes, THE PROJECT SHALL publish requirement-mapped QA, deterministic evidence,
an AI-eval rubric covering provenance/grounding/leakage/authority/calibration honesty, and a Project
Log entry explaining (1) what was built and which evidence problem it solves, (2) which code/data
contracts changed, (3) why the source, split, metric, and authority decisions were made, and (4)
which Gates or limitations remain. An engineering PASS SHALL remain separate from the measured
resolver-quality result.

## MVP scope

- Audit available sources and make permission/publication/ground-truth status machine-checkable.
- Define and validate the versioned case, provenance, authority, label, split, manifest, raw-run, and
  report contracts.
- Obtain explicit owner decisions before using a source or publishing its content.
- Build one 60-case representative pilot only if all exact-label and source Gates can be satisfied.
- Add label-blind Test collection and separate scoring.
- Add retrieval, ranking, resolver-decision, calibration, failure-taxonomy, and ablation evidence.
- Freeze all artifacts with checksums and close with QA, evidence, AI eval, and Project Log.

## Out of scope / deferred

- The 300–500-case scale target beyond a separately approved expansion plan.
- Unauthorized scraping or assumed marketplace/Fandom access.
- Images, OCR, seller identities, pricing analysis, or private user content.
- Automatic canonical promotion from Human Knowledge, Wiki data, workbooks, or nearest candidates.
- Training/tuning/replacing retrieval, calibration, Pointwise, Listwise, or runtime policy.
- Re-running the completed neural comparison before a non-saturated frozen benchmark exists.
- Production-accuracy, real-marketplace-generality, statistical-significance, or production-readiness
  claims from the 60-case pilot.

## Known starting state

- `data/benchmark.json`: 100 synthetic/curated cases; 58 Train, 21 Development, 21 Test; 60 matched,
  20 ambiguous, 20 no-match overall; only 12 matched Test ranking targets.
- `data/catalog.json`: 120 synthetic/curated products (`fixture-v1`).
- `data/human_labeled_names.json`: 101 real noisy human-labeled scans.
- `data/human_labeled_catalog_alignment.json`: 0 exact canonical mappings, 2 family-only, 99
  unmapped; therefore it is not an exact-variant benchmark today.
- Owner release workbooks: 1,763 review-only observations with no canonical links and publication
  rights not established.
- Checked-in Wiki pilot: licensed/attributed text derivatives with 100 release rows, but expressly
  held outside canonical truth and evaluation labels.
