# Representative Hard Benchmark v1 — Tasks

Date: 2026-09-26. Mode: Lite / Lean Industrial. Status:
**RHB-T1–T4 COMPLETE; HISTORICAL RHB-T4 BLOCKED CHECKPOINT PRESERVED; VERSIONED RHB-T4 RE-AUDIT
PASSES THE EXACT-AUTHORITY GATE; RHB-T5 PRE-AUTHORING REPAIR COMPLETE; RHB-T5+ NOT STARTED OR
AUTHORIZED**.

Each task is intended to be one independently reviewable commit. Tasks that require an owner decision
are explicit Gates, not implementation steps that an agent may infer or bypass.

## Phase A — Schema, tooling, and source readiness

### RHB-T1 — Freeze the current evidence baseline `[qa/doc_curator]`

- [x] Record machine-checkable counts/checksums and declared usage boundaries for the 100-case
  fixture benchmark, 120-product fixture catalog, 101 human-labeled scans, catalog alignment,
  1,763-row local release snapshot, and checked-in Wiki pilot. _(→RHB-R1,RHB-R7,RHB-R19)_

Files:

- `scripts/build_representative_hard_benchmark_source_inventory.py`
- `tests/evaluation/test_representative_hard_benchmark_source_inventory.py`
- `data/evaluation/representative-hard-benchmark-v1/source-inventory.json`
- `data/evaluation/representative-hard-benchmark-v1/source-inventory-manifest.json`
- `docs/evidence/representative-hard-benchmark-source-baseline.md`

Acceptance:

- The inventory reproduces the known `0 exact / 2 family-only / 99 unmapped` real-scan alignment and
  never describes staged/review-family rows as canonical truth.
- Running the baseline check twice is byte-identical or returns `unchanged`; no network is used.

### RHB-T2 — Implement strict benchmark contracts `[backend]`

- [x] Add allowlisted schemas and fail-closed validators for source inventory, canonical authority,
  query pack, labels, split, manifest, label-blind raw, and scored results. _(→RHB-R2,RHB-R5–R9,RHB-R19,RHB-R21)_

Files:

- `src/product_variant_resolver/representative_benchmark.py`
- `tests/evaluation/test_representative_benchmark_contract.py`
- `data/evaluation/representative-hard-benchmark-v1/README.md`

Acceptance:

- Negative tests reject unauthorized/publication-unknown sources, unknown fields, invalid status/UUID
  combinations, held scored rows, family-only canonical claims, stale hashes and partial writes.
- The implementation imports no network/browser client and does not modify runtime services.

### RHB-T3 — Obtain the owner source decision **GATE** `[task_executor/doc_curator]`

- [x] Present the exact proposed source/use/publication matrix and record the owner's decisions for
  query text, evidence retention, reviewer identity, local-only use, and public Git artifacts.
  _(→RHB-R2–R4,RHB-R21)_

Files:

- `specs/representative-hard-benchmark-v1/source-approval.md`
- `data/evaluation/representative-hard-benchmark-v1/source-decisions.json`

Acceptance:

- Every proposed source/use pair is `approved`, `rejected`, or `held`; no blank or implied approval.
- No eBay/Mercari/Facebook/Fandom collection is authorized merely by completing this task.
- If no suitable source is approved, close the Gate as blocked and do not begin case authoring.

### RHB-T4 — Audit catalog-ground-truth eligibility **GATE** `[qa/doc_curator]`

- [x] **COMPLETE — GATE BLOCKED.** Validate which existing canonical records, if any, have
  source-independent exact-variant authority suitable for a non-synthetic matched benchmark.
  _(→RHB-R5–R7,RHB-R9)_

Files:

- `data/evaluation/representative-hard-benchmark-v1/canonical-authority.json`
- `data/evaluation/representative-hard-benchmark-v1/canonical-authority-manifest.json`
- `docs/evidence/representative-hard-benchmark-authority-audit.md`

Acceptance:

- Each eligible UUID binds a catalog/product checksum, independently reviewed evidence, fields,
  reviewer and timestamp.
- If fewer than 20 pilot-usable exact variants or fewer than four same-casting multi-release families
  are eligible, record the shortfall and stop matched pilot construction; do not infer UUIDs.
- Audit result: `0` pilot-usable exact variants and `0` eligible multi-release families; shortfall is
  `20` variants and `4` families. T5 remains prohibited until new authorized exact-variant evidence
  passes a new source decision and authority audit.

### RHB-T4 re-audit readiness — Preserve history and evaluate CAR-T5F `[qa/doc_curator]`

- [x] Add a fail-closed, versioned adapter that independently revalidates the 20-record CAR-T5F
  authority bundle, recomputes seven qualifying families and zero shortfalls, and proposes
  `passed_exact_authority_gate` without writing a new authority artifact or changing the historical
  blocked checkpoint.
- [x] After a separate CAR-T6 owner authorization, materialize the new re-audit authority artifact
  and manifest. The result contains 20 exact variants across seven qualifying families, zero
  shortfalls and `passed_exact_authority_gate`; it is a new versioned result, not an edit to the
  historical RHB-T4 files.

The CAR-T6 authorization and re-audit do not authorize RHB-T5, query-pack authoring or label
authoring. The old `canonical-authority.json` and `canonical-authority-manifest.json` remain the
immutable evidence of the earlier honest blocked result. RHB-T5 still requires a separate owner
Gate despite the new RHB-T4 PASS.

## Phase B — Owner-reviewed pilot tranche

### RHB-T5 readiness — Validate the authoring boundary `[qa/doc_curator]`

- [x] Revalidate the T1/T3 source boundary and versioned RHB-T4 PASS, count usable real query
  candidates, confirm that no T5/T6 artifact exists, and identify every prerequisite that must be
  repaired before a separate RHB-T5 Owner Gate.

Files:

- `src/product_variant_resolver/representative_benchmark_query_readiness.py`
- `scripts/validate_representative_hard_benchmark_query_readiness.py`
- `tests/evaluation/test_representative_benchmark_query_readiness.py`
- `docs/evidence/representative-hard-benchmark-query-readiness.md`

Acceptance:

- The check is deterministic and read-only; it does not import the resolver, view live output, make
  network requests, create a query pack, create labels, or grant RHB-T5 authorization.
- It proves whether 60 unique non-synthetic query candidates exist and fails closed on source,
  authority, historical-checkpoint, permission, checksum, or premature-artifact drift.
- It explicitly detects that the raw human source contains adjacent pipeline outputs/labels, that
  its raw rows are local-only, and that `BenchmarkQuery.split` currently precedes the RHB-T7 split
  phase.
- Result: source capacity passes (`91` unique nonblank candidates for a `60`-case target), CAR-T6
  passes (`20` exact variants / `7` qualifying families / `0` shortfalls), but RHB-T5 remains
  blocked pending an output-blind local projection, publication-path repair, split-contract
  alignment, a fresh authoring context, and a separate Owner Gate.

### RHB-T5 pre-authoring repair — Close projection/publication/split gaps `[backend/qa/doc_curator]`

- [x] Materialize a deterministic private query-only projection, publish only its aggregate
  manifest, and remove split assignment from the T5 query contract. _(→RHB-R2,RHB-R13,RHB-R19,RHB-R21)_

Files:

- `src/product_variant_resolver/representative_benchmark_query_projection.py`
- `scripts/build_representative_hard_benchmark_query_projection.py`
- `data/evaluation/representative-hard-benchmark-v1/query-authoring-source-manifest.json`
- `data/evaluation/representative-hard-benchmark-v1/local-query-authoring-v1/` _(Git-ignored)_
- `tests/evaluation/test_representative_benchmark_query_projection.py`

Acceptance:

- The private artifact contains exactly 91 unique rows and only `source_record_ref` + `query`; it is
  ignored, stored under a `0700` directory as `0600`, and reproduces as `unchanged`.
- The tracked manifest contains only the approved aggregate fields, record count and irreversible
  projection hash; it contains no row-level query, output, label or failure-category content.
- `BenchmarkQuery` rejects a premature `split`; RHB-T7 remains the sole split owner through the
  separate `SplitArtifact`, and cross-family/evidence leakage checks still pass.
- Readiness v2 is `ready_for_separate_owner_authorization`, not `rhb_t5_authorized`; a fresh
  output-blind context and exact RHB-T5 Owner Gate are still mandatory.

### RHB-T5 — Author the output-blind 60-case pilot query pack `[qa/doc_curator]`

- [ ] After Gates T3/T4 pass, author exactly 60 non-synthetic cases without viewing resolver output,
  group duplicate evidence events, and cover every required challenge class. _(→RHB-R8,RHB-R10–R11)_

Files:

- `data/evaluation/representative-hard-benchmark-v1/local-query-authoring-v1/query-pack.json`
- `data/evaluation/representative-hard-benchmark-v1/query-pack-manifest.json`
- `docs/evidence/representative-hard-benchmark-query-authoring.md`

Acceptance:

- Query pack contains no expected status/UUID/correctness/rank and declares
  `resolver_output_viewed=false` for every row; it contains no Development/Test split.
- Duplicate, synthetic-quota, challenge-coverage, publication and privacy checks pass before labels.

### RHB-T6 — Record owner labels and held cases `[qa/doc_curator]`

- [ ] Present source/authority evidence without resolver candidates; record attributable owner labels
  and reasons; quarantine any unresolved item as held. _(→RHB-R5–R11,RHB-R20–R21)_

Files:

- `data/evaluation/representative-hard-benchmark-v1/local-query-authoring-v1/labels.json`
- `data/evaluation/representative-hard-benchmark-v1/local-query-authoring-v1/held-labels.json`
- `data/evaluation/representative-hard-benchmark-v1/labels-manifest.json`

Acceptance:

- Approved scored labels are exactly 20 matched, 20 ambiguous, 20 no-match; every matched label has a
  validated authority ID and UUID.
- At least 12 matched cases across four families are declared same-casting/different-release hard
  negatives; held items do not count toward 60.

### RHB-T7 — Build and freeze the family-safe benchmark `[backend/qa]`

- [ ] Construct connected family/evidence groups, allocate deterministic Development/Test splits,
  and freeze all parent checksums/configuration/exclusions. _(→RHB-R12–R14,RHB-R19)_

Files:

- `data/evaluation/representative-hard-benchmark-v1/benchmark-manifest.json`
- `tests/evaluation/test_representative_benchmark_split.py`

Acceptance:

- No family, canonical family, duplicate listing, alias event, or evidence event crosses splits.
- Split is approximately 20 Development / 40 Test subject to group safety, and achieved status/tag
  counts are explicit.
- Test labels live in a separate artifact and no build step exposes them to retrieval/model code.

## Phase C — Evaluation and evidence

### RHB-T8 — Implement candidate, ranking, and decision metrics `[backend]`

- [ ] Extend the offline evaluator with Recall@5/10/25/50, empty-candidate rate, Top-1, MRR@10,
  NDCG@10, hard-negative accuracy, precision, coverage, false-match, abstention, wrong-identity,
  under/over-abstention and failure slices. _(→RHB-R15,RHB-R16,RHB-R20)_

Files:

- `src/product_variant_resolver/representative_benchmark.py`
- `tests/evaluation/test_representative_benchmark_metrics.py`

Acceptance:

- Hand-computed fixtures prove every numerator, denominator, retrieval-miss treatment and zero-
  denominator `not_applicable` result.
- Candidate-generation and ranking sections use separate fields and cannot hide retrieval misses.

### RHB-T9 — Implement calibration and risk/coverage evidence `[backend]`

- [ ] Add fixed-bin ECE, Brier score, reliability rows, precision/coverage and risk/coverage sweeps
  over predeclared thresholds. _(→RHB-R16–R17)_

Files:

- `src/product_variant_resolver/representative_benchmark.py`
- `tests/evaluation/test_representative_benchmark_calibration.py`

Acceptance:

- Tests cover bin boundaries, empty bins, incorrect UUIDs with high confidence, abstentions, curve
  denominators and exact recomputation from case rows.
- No Test-derived threshold or calibrator is written to runtime configuration.

### RHB-T10 — Implement read-only retrieval ablations `[backend]`

- [ ] Evaluate the eight declared retrieval/ranking arms over identical frozen inputs without
  changing production defaults; mark structurally unavailable arms explicitly. _(→RHB-R18,RHB-R22)_

Files:

- `src/product_variant_resolver/representative_benchmark.py`
- `tests/evaluation/test_representative_benchmark_ablation.py`

Acceptance:

- Comparable arms receive identical queries/catalog/version and report raw target ranks.
- The task does not enable the heuristic reranker in `/resolve`, change RRF, or invoke neural models.

### RHB-T11 — Collect the one-time label-blind Test raw `[task_executor/qa]`

- [ ] Verify every frozen input, run Test collection once without importing labels, freeze raw output
  and manifest, and prove a repeat is `unchanged`. _(→RHB-R13–R14,RHB-R19,RHB-R22)_

Files:

- `reports/representative-hard-benchmark-v1/test-raw.json`
- `reports/representative-hard-benchmark-v1/test-raw-manifest.json`
- `tests/evaluation/test_representative_benchmark_label_blindness.py`

Acceptance:

- Recursive raw inspection finds no expected label, target, correctness, aggregate metric, gate, or
  winner field; collection telemetry proves Test labels were never loaded.
- Source/config/catalog/query/implementation hashes match the frozen manifest before and after run.

### RHB-T12 — Score and publish the pilot report `[backend/qa]`

- [ ] Join frozen raw to labels without reretrieval; produce deterministic JSON, Markdown,
  precision–coverage, risk–coverage, reliability and ablation artifacts with exact denominators and
  failure taxonomy. _(→RHB-R14–R20)_

Files:

- `reports/representative-hard-benchmark-v1/evaluation.json`
- `reports/representative-hard-benchmark-v1/evaluation.md`
- `reports/representative-hard-benchmark-v1/*.svg`
- `tests/evaluation/test_representative_benchmark_measured_artifacts.py`

Acceptance:

- Every aggregate is recomputable from ordered case results and raw counts.
- The report identifies the 60-case pilot, exact Test/matched denominators, catalog/source scope,
  exploratory calibration, quality failures, and no production/general-accuracy claim.
- A valid poor resolver result is published and does not fail the engineering artifact build.

### RHB-T13 — Close Lean QA and documentation `[qa/doc_curator]`

- [ ] Run focused/full regression, map RHB-R1–R23, publish technical evidence and AI-eval rubric,
  update README/Portfolio Guide only with measured scoped claims, and append the required narrative
  Project Log entry. _(→RHB-R21–R23)_

Files:

- `specs/representative-hard-benchmark-v1/review.md`
- `docs/evidence/representative-hard-benchmark-v1.md`
- `docs/evidence/ai-evals/representative-hard-benchmark-v1.md`
- `docs/PROJECT-LOG.md`
- `README.md`
- `docs/PORTFOLIO-GUIDE.md`

Acceptance:

- QA records separate engineering/data-quality and resolver-quality verdicts.
- Full suite, focused tests, Ruff, strict MyPy, compileall, deterministic `--check`, artifact/link/hash
  validation and `git diff --check` are recorded.
- Project Log explains the work, problem, changed contracts, decisions/trade-offs and remaining Gates,
  not merely a checklist of files.

### RHB-T14 — Decide whether to plan 300–500-case expansion **GATE** `[strategic_planner/doc_curator]`

- [ ] Review pilot label cost, source stability, authority yield, family/challenge coverage, failure
  distribution and privacy/publication constraints; either approve a separate expansion brief or
  record why scale-up is held. _(→RHB-R12,RHB-R23)_

Files:

- `specs/representative-hard-benchmark-v1/expansion-decision.md`
- `docs/PROJECT-LOG.md`

Acceptance:

- The decision never auto-starts collection and never treats synthetic/duplicate/generated cases as
  quota progress.
- Neural reranking remains deferred until a frozen non-ceiling benchmark exists and a separate model
  comparison protocol is approved.

## Requirement traceability

| Requirement | Primary tasks |
|---|---|
| RHB-R1 | T1 |
| RHB-R2 | T1–T3 |
| RHB-R3 | T2–T3 |
| RHB-R4 | T3 |
| RHB-R5 | T2, T4, T6 |
| RHB-R6 | T2, T4, T6 |
| RHB-R7 | T1, T4, T6 |
| RHB-R8 | T2, T5–T6 |
| RHB-R9 | T2, T6 |
| RHB-R10 | T5–T6 |
| RHB-R11 | T5–T7 |
| RHB-R12 | T7, T14 |
| RHB-R13 | T7, T11 |
| RHB-R14 | T7, T11–T12 |
| RHB-R15 | T8, T12 |
| RHB-R16 | T8–T9, T12 |
| RHB-R17 | T9, T12 |
| RHB-R18 | T10, T12 |
| RHB-R19 | T1–T2, T7, T11–T12 |
| RHB-R20 | T8, T12 |
| RHB-R21 | T1–T3, T5–T6, T13 |
| RHB-R22 | T10–T13 |
| RHB-R23 | T13–T14 |

## Dependency order

```text
T1 -> T2 -> T3 owner source Gate
                  |
                  v
             T4 authority Gate
                  |
                  v
         T5 -> T6 -> T7
                  |
          T8 -> T9 -> T10
                  |
            T11 -> T12 -> T13
                              |
                              v
                         T14 expansion Gate
```

T5 cannot start if either T3 or T4 is blocked. T11 cannot run before all code/config/data hashes and
the Test lifecycle are frozen. T12 cannot rerun retrieval. T14 may recommend a later milestone but
cannot authorize collection, canonical promotion, neural reranking, or runtime changes.
