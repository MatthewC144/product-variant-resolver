# Representative Hard Benchmark v1 — Lean QA Review

Date: 2026-10-05. Mode: Lite / Lean Industrial. Scope:
**RHB-T1/T2 history + RHB-T3/T4 final QA + RHB-T5 authoring + RHB-T6 readiness**.

## Current milestone verdict: RHB-T6 READINESS VALIDATOR PASS / OWNER GATE NOT REQUESTABLE

The read-only RHB-T6 validator now replays the private RHB-T5 pack through the core query validator,
revalidates T1/T3 and the 20-record CAR authority bundle, checks label-artifact absence, and emits a
deterministic hash-bound report without writing labels or authorization. Its readiness SHA-256 is
`b4bf8f9a45b315a2ad64ba9f5626daef63a246c66bbbfc884856b7945e1b9f45`.

The engineering check passes, but the Owner Gate is not yet requestable. All 60 queries use
`human-labeled-real-noisy-v1`, whose frozen T3 decision permits only `ambiguous` and `no_match`;
maximum source-permitted matched labels are therefore `0/20`. The 20 CAR exact records use the
Wiki pilot evidence source, which frozen T1/T3 still marks `prohibited/staging_only` for exact
authority. Provisional challenge shortfalls also remain `16` across five classes. The next legal
action is a separately approved versioned source-decision and authority-admission repair—not label
authoring.

During readiness integration, QA found that the RHB-T5 builder used the truthful independent-agent
author role while the historical core validator allowed only `project_owner`; the builder had
constructed a Pydantic-valid pack without the cross-artifact validator. The repair now permits the
fixed independent-agent role only for local-only Human queries, keeps arbitrary/public authors
blocked, and makes the builder call `validate_query_pack()` directly. This closes the bypass before
any label validator can consume the pack.

All 118 representative-benchmark tests pass. Ruff/format, strict MyPy across the four touched
source/CLI modules, compile, query-pack replay and diff checks pass. A full-repository run showed no
failure through the displayed 5% checkpoint and later progress, then was manually stopped after
approximately 2.5 minutes under Lite mode because unrelated model/evaluation tests are slow; no new
full-suite PASS is claimed.

## Previous milestone verdict: RHB-T5 AUTHORING ARTIFACT PASS / COVERAGE GATE BLOCKED

RHB-T1 through RHB-T3 remain PASS, and the historical zero-authority RHB-T4 blocked checkpoint is
preserved below. The separately authorized CAR-T6 versioned re-audit now passes the exact-authority
Gate with 20 exact variants, seven qualifying families and zero shortfalls.

The owner then authorized RHB-T5 with an exact local-only boundary. A fresh independent agent used
only the Git-ignored query projection and produced 60 unique non-synthetic query/source/evidence
rows across 53 provisional family groups. The private pack contains no expected outcome, UUID,
correctness, rank or split; the public manifest contains aggregates and hashes only. RHB-T6,
RHB-T7 and resolver evaluation remain unauthorized.

The 60-row artifact is valid, deterministic and private, but is not an accepted representative
pilot. Provisional query-surface shortfalls remain for conflicting year `3`, color `3`, series `4`,
identifier `2`, and unknown-to-catalog `4`. Catalog-relative absence is intentionally not guessed
from query text. The overall RHB-T5 checkbox therefore remains open under RHB-R10/R11. Earlier
T1/T2/T3/T4 and pre-authoring QA history remains below.

## RHB-T5 output-blind authoring verdict: ENGINEERING PASS / DATA GATE BLOCKED

The materialized private query pack contains exactly 60 case IDs, 60 case-insensitive unique queries,
60 unique opaque source references and 60 unique evidence-event groups. It uses a `0700` directory
and `0600` files, is positively Git-ignored, and reproduces as `unchanged / unchanged`. The public
manifest is `0644`, contains no row-level content, and binds the private bytes at SHA-256
`97f7f0dd61cf619bb16b198778356d8ef53c7a504086f11542922f90706a858a`.

The authoring contract validates the exact Owner Gate hash, ensures the authoring time does not
predate authorization, revalidates T1/T3 scope and projection checksums, rejects duplicate query or
evidence rows, rejects singleton-family same-casting tags, and prohibits query-only inference of
`unknown_to_catalog`. It sets `representative_pilot=false`, `challenge_coverage_verified=false`, and
publishes exact provisional shortfalls instead of padding them or overstating completion.

All 112 representative-benchmark tests pass. Ruff and format checks pass, strict MyPy reports no
issues in the three touched source/CLI modules, compile succeeds, `git diff --check` passes, and the
authoring check replay is deterministic. An initial QA pass caught overclaimed challenge semantics
and public owner-text coupling; the fresh authoring agent corrected both before this verdict. No
label, split, resolver, RAG, embedding, Pointwise or Listwise evaluation occurred.

## Historical RHB-T5 readiness v1: PASS (validator) / BLOCKED (authoring Gate)

The deterministic validator rechecks T1/T3, CAR-T6, historical T4 hashes, real-query capacity,
artifact absence and the current query schema without writing any file or importing the resolver.
Its real report is hash-bound at
`9a2f5491a6c22c097eaf8bd913c53a46dab71068b1484906f91c48f7b030c840`.

Focused verification passes 82 tests: six direct readiness tests plus 76 related RHB/CAR contract
tests. Ruff/format/diff checks pass, and strict MyPy reports zero issues for the benchmark contract,
readiness and CAR-T6 re-audit modules. The negative suite rejects source checksum drift, CAR-T6
authority tampering and premature query/label artifacts. A full-repository run reached 10% with no
failure before being manually stopped due to unrelated long-running evaluation tests; no new
full-suite PASS is claimed.

Historical required action, now completed: implement a Git-ignored query-only projection, separate
local raw rows from the public aggregate manifest, defer split allocation to RHB-T7, and rerun
readiness. The fresh explicit RHB-T5 Owner Gate remains outstanding. No query selection,
challenge-coverage decision, labels, resolver run or benchmark-quality claim is accepted by this
review.

## RHB-T5 pre-authoring repair verdict: PASS / OWNER GATE STILL CLOSED

The deterministic projection contains 91 unique rows and exactly two row fields:
`source_record_ref` and `query`. The private directory/file use `0700/0600`, the exact `.gitignore`
rule is verified, and creation plus check replay returns `created / unchanged`. The tracked public
manifest contains only the T3-approved aggregate fields and binds private bytes at SHA-256
`d5712684cf73c29dd9ea7f385f78c03eb1c8300ce35afd477c0d09ad0d9032dd`.

The query contract now rejects `split` as an unknown authoring field. The separate RHB-T7 split
validator still requires every case exactly once and rejects family/evidence groups crossing
Development/Test. Readiness v2 validates the materialized projection, ignore rule, permissions,
CAR-T6 20/7/0 authority and absence of query/label artifacts; its report hash is
`5b2582049420406f0acf5577bcca17f22f0834e598e87838c294625cdf300d30`.

This PASS authorizes no dataset construction. The only remaining readiness blockers are
`fresh_output_blind_authoring_context_required` and `rhb_t5_owner_gate_required`. The current
inspection/build session must not author the 60 rows, and an ordinary continuation cannot substitute
for the exact Owner Gate.

## RHB-T1 historical verdict: PASS

RHB-T1 now produces a truthful, deterministic and clean-checkout-portable source baseline. The two
earlier blockers are resolved:

1. all six entries separate current repository/publication reality from known rights evidence and
   prospective RHB-v1 use/redistribution; and
2. the 1,763-row owner aggregate is now read only from the Git-tracked
   `reports/local-release-staging-v1/manifest.json`, while the ignored local review summary is not a
   required input and is not listed in the repository tracking contract.

The inventory still authorizes no new source use. Human-label rows and their alignment are recorded
as already public/Git-tracked, but future benchmark use and republication remain blocked pending
RHB-T3. Owner workbook rows remain private and untracked; only aggregate counts and non-reversible
checksums are public.

## Checked items

- All six source entries' current repository/publication state, known rights evidence, prospective
  benchmark use, prospective redistribution, owner decision and authority boundary.
- Human labels/alignment: current row-level publication is explicit; future use/republication is
  blocked pending RHB-T3; existing publication is not treated as new permission.
- Owner snapshot: 1,763 private observations remain untracked; the tracked public manifest contains
  only counts/checksums; the ignored review summary is absent from required inputs and contracts.
- Wiki pilot: 100 attributed public text rows remain staging-only, without canonical UUIDs or new
  collection authority.
- Counts/checksums, `0 exact / 2 family-only / 99 unmapped`, zero owner promotions/links, zero
  network requests and zero copied private owner rows.
- Every path in `repository_tracking_contract.artifacts` is verified with
  `git ls-files --error-unmatch`.
- A fresh-clone-shaped temporary tree containing only public inputs can build the baseline.
- Repeated deterministic checks, focused tests, Ruff, format, strict MyPy, compileall and
  `git diff --check`.
- Allowed scope: no product/runtime/API/model/database source file changed.

## Requirement coverage

| Requirement | Evidence | Result |
|---|---|---|
| RHB-R1 | Six entries record origin, acquisition, count, checksum, current publication/repository state, known rights, prospective use/redistribution and unresolved owner decisions. Public human artifacts, private owner rows/public aggregate, and attributed Wiki derivatives are represented accurately. | PASS |
| RHB-R7 | Human Knowledge/family alignment, owner staging and Wiki staging remain non-canonical. Alignment is `0 exact / 2 family-only / 99 unmapped`; owner promotions/links are zero; Wiki canonical UUIDs are null. | PASS |
| RHB-R19 | Stable JSON, schema/version metadata, generator/input/inventory hashes, exact counts/order, atomic output, drift rejection, repeated `unchanged`, Git tracking validation and fresh-clone-shaped public-input construction all pass. | PASS |

## Findings

### Blocker

- None.

### Important

- None for RHB-T1.

### Later

- RHB-T3 must still obtain explicit owner decisions for every future source/use/publication pair.
  This T1 PASS records present facts only and does not authorize benchmark reuse, republication,
  collection, labeling or canonical promotion.
- Exact real-variant authority remains absent. RHB-T4 must independently prove any matched UUID;
  neither family context nor staged release rows can supply it.

## Reproduction and evidence

```text
.venv/bin/python scripts/build_representative_hard_benchmark_source_inventory.py --check
unchanged

.venv/bin/python scripts/build_representative_hard_benchmark_source_inventory.py --check
unchanged

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py
7 passed in 0.17s

.venv/bin/ruff check --select F,I \
  scripts/build_representative_hard_benchmark_source_inventory.py \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py
All checks passed!

.venv/bin/ruff format --check \
  scripts/build_representative_hard_benchmark_source_inventory.py \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py
2 files already formatted

.venv/bin/mypy --strict --follow-imports=skip \
  scripts/build_representative_hard_benchmark_source_inventory.py \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py
Success: no issues found in 2 source files

.venv/bin/python -m compileall -q \
  scripts/build_representative_hard_benchmark_source_inventory.py \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py src
PASS

git diff --check
PASS
```

Independent tracking verification:

```text
TRACKED data/benchmark.json
TRACKED data/catalog.json
TRACKED data/human_labeled_names.json
TRACKED data/human_labeled_catalog_alignment.json
TRACKED reports/local-release-staging-v1/manifest.json
TRACKED data/external/hot-wheels-wiki/pilot-2025/manifest.json
TRACKED data/external/hot-wheels-wiki/pilot-2025/normalized.json
TRACKED data/external/hot-wheels-wiki/pilot-2025/raw.json
```

The ignored path
`data/external/hot-wheels-wiki/local-release-casting-review-v1/manifest.json` is verified as
untracked/ignored and appears in neither `input_artifacts` nor
`repository_tracking_contract.artifacts`.

## Recommended next task

The historical T1 recommendation was to proceed to RHB-T2 while preserving the T1 source and
publication boundaries. The RHB-T2 result below supersedes that recommendation for current work.

---

## RHB-T2 initial QA

### Verdict: FAIL

The implementation provides useful strict Pydantic contracts and passes its 18 authored tests, T1
regression, API/catalog regression, Ruff, formatting and product-module MyPy. It correctly rejects
unknown fields, unapproved source use, invalid status/UUID combinations, held/rejected scored rows,
cross-split family leakage, recursively forbidden Test-raw keys, stale manifests and partial state.
It also remains isolated from network, browser, FastAPI, resolver-service and catalog mutation code.

It cannot pass Lean G2, however. An `approved_exact` record may omit available variant-defining
catalog fields, and a staging source can become exact canonical authority merely by changing
permission/use declarations even though RHB-R5/R7 expressly prohibit staged rows from establishing
truth. Public authority and label records also accept obvious contact information outside the query
field. These are executable counterexamples, not documentation-only concerns. Strict MyPy also
fails in the new test file.

### Checked items

- Strict allowlist schemas for source inventory/manifest, canonical authority, query pack, labels,
  split, frozen manifest, label-blind raw and scored results.
- Negative cases for unknown fields, pending/unauthorized use, invalid UUID/status combinations,
  held/rejected scoring, missing/split-leaking rows, recursively forbidden raw keys, raw
  order/count, stale artifact/parent hashes and partial state.
- Exact canonical UUID/catalog version/record checksum binding and authority-before-label ordering.
- RHB-R5 requirement that every available variant-defining field be covered by exact authority.
- RHB-R7 separation of canonical truth from staged and family/review evidence.
- Public/private permission and obvious PII handling across query, authority and label artifacts.
- No network/browser/runtime imports; no changes to FastAPI, resolver service, runtime policy,
  canonical catalog or database code.
- Focused T2 tests, T1 regression, API/catalog regression, Ruff F/I, Ruff format, strict MyPy,
  compileall, full pytest and `git diff --check`.
- Task status: T2 is checked complete in `tasks.md`, but must return to incomplete/in review until
  this FAIL is corrected and independently rechecked.

### Requirement coverage

| Requirement | Evidence | Result |
|---|---|---|
| RHB-R2 | Unapproved/pending sources and public-row use without retention/redistribution permission are rejected. Unknown schema fields are forbidden. | PASS |
| RHB-R5 | UUID, catalog version and record checksum are bound, but `approved_exact` requires only `casting` and `release_year`; it accepts omission of non-null `series`, `color`, `collector_number`, `series_position` and `identifiers`. | FAIL |
| RHB-R6 | Status/UUID combinations and held/rejected scoring are rejected, but a falsely accepted incomplete/staged authority can still make a matched label score-eligible. | FAIL (downstream) |
| RHB-R7 | Current pending staging rows are rejected, but their non-canonical `authority_boundary` is free text and unenforced; after changing approval/use fields, the same staged source is accepted as exact authority. | FAIL |
| RHB-R8 | Versioned label fields, enum combinations, unknown fields, review status, reviewer/time/reason and score eligibility are validated. | PASS |
| RHB-R9 | `matched` requires UUID/authority; `ambiguous` and `no_match` cannot carry canonical identity. | PASS |
| RHB-R19 | Generic manifest rejects stale artifact hash, stale/incomplete parent set, wrong order/count and partial status; raw/scored artifacts enforce complete state and exact row order. | PASS for T2 contract scope |
| RHB-R21 | Query text rejects obvious email/phone PII when public-safe, but public authority/label metadata accepts obvious email/phone contact data. | FAIL |

### Findings

#### Blocker

1. **Exact authority does not cover every available variant-defining field (return to Phase 2).**
   `validate_canonical_authority` constructs the required set as only `casting` and
   `release_year`. The first fixture product also has non-null `series`, `color`,
   `collector_number`, `series_position` and `identifiers`; an authority declaring only casting and
   year still validates. This violates RHB-R5 and can falsely bless one release variant when another
   differs by color, collector number, series or identifier.

2. **Staging/family authority separation is permission-mutable rather than fail-closed (return to
   Phase 2).** The staged-source test passes only because today's inventory says the source is
   pending. `authority_boundary` is an unconstrained string. When the owner snapshot is changed to
   approved/public/exact-authority use, `validate_canonical_authority` accepts it. RHB-R5/R7 state
   that staged release rows, family-only decisions, Human Knowledge and model/retrieval suggestions
   cannot establish exact canonical truth even if they are useful evidence. The contract needs an
   enforced authority-eligibility boundary, not only mutable permission flags.

3. **Public authority/label records can contain obvious contact PII (return to Phase 2).** The PII
   check applies only to `BenchmarkQuery.query`. Public `reviewed_by`, `family_label`,
   `review_reason`, `evidence_refs` and corresponding authority metadata have no equivalent
   validation. A public authority/label pair containing `person@example.com` and
   `+1 (212) 555-0123` validates, contrary to RHB-R21.

4. **Strict MyPy fails for the new test surface (return to Phase 2).** Running strict MyPy over the
   implementation and its focused test reports
   `tests/evaluation/test_representative_benchmark_contract.py:480: error: Value of type
   "Collection[Collection[str]]" is not indexable [index]`. Lean G2 requires no type errors.

#### Important

- `tasks.md` currently marks RHB-T2 complete despite this QA FAIL. It should not advertise completion
  until the repair and recheck pass.
- The full suite has one pre-existing README measured-artifact failure: the neural-reranker evidence
  test expects the exact phrase `**100-case synthetic/curated fixture benchmark**`. The result is
  `999 passed, 1 failed`. This failure is outside the T2 files and was previously known, so it is not
  the cause of the T2 verdict; nevertheless Lean G3 cannot close for the milestone until the test
  and truthful README contract agree.
- A query pack marked `publication_scope=aggregate_only` can still contain raw query rows. This may
  be valid only if the row artifact remains outside Git and a separate aggregate is published. The
  later writer/publication Gate must enforce that placement explicitly; otherwise RHB-R21 can be
  bypassed by committing an aggregate-only-labelled row artifact.

#### Later

- T3 source approval and T4 authority audit remain mandatory Gates. Passing schema validation must
  never be described as source approval or proof that exact real-variant authority exists.
- Scored metric arithmetic and report recomputation belong to T8/T12; this T2 review validates only
  the declared structural/cross-artifact boundaries.

### Reproduction and evidence

Focused and regression tests:

```text
PYTHONPATH=src .venv/bin/pytest -o addopts='' -q \
  tests/evaluation/test_representative_benchmark_contract.py
18 passed in 0.07s

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py
7 passed in 0.16s

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q \
  tests/api tests/integration/test_catalog_service.py tests/test_fixture_data.py \
  tests/unit/test_retrieval_policy.py
66 passed, 1 warning in 4.59s
```

Executable negative probes:

```text
# Exact authority containing only casting+release_year against a product whose other
# variant fields are populated.
VALIDATED authority-001
OMITTED_NON_NULL ['series', 'color', 'collector_number', 'series_position', 'identifiers']

# Same existing owner staging source after mutable approval/use fields are set.
STAGED_ACCEPTED authority-001 owner-local-release-snapshot-2023-2026-v1

# Public authority/label metadata with obvious contact data.
PUBLIC_PII_ACCEPTED PublicationScope.public person@example.com Call +1 (212) 555-0123
```

Static/tooling checks:

```text
.venv/bin/ruff check --select F,I \
  src/product_variant_resolver/representative_benchmark.py \
  tests/evaluation/test_representative_benchmark_contract.py
All checks passed!

.venv/bin/ruff format --check \
  src/product_variant_resolver/representative_benchmark.py \
  tests/evaluation/test_representative_benchmark_contract.py
2 files already formatted

.venv/bin/mypy --strict src/product_variant_resolver/representative_benchmark.py
Success: no issues found in 1 source file

.venv/bin/mypy --strict \
  src/product_variant_resolver/representative_benchmark.py \
  tests/evaluation/test_representative_benchmark_contract.py
tests/evaluation/test_representative_benchmark_contract.py:480: error: Value of type
"Collection[Collection[str]]" is not indexable  [index]
Found 1 error in 1 file (checked 2 source files)

.venv/bin/python -m compileall -q src \
  tests/evaluation/test_representative_benchmark_contract.py
PASS

git diff --check
PASS
```

Full regression:

```text
PYTHONPATH=src .venv/bin/pytest -o addopts='' -q
999 passed, 1 failed, 1 warning in 94.63s

FAILED tests/evaluation/test_neural_reranker_measured_artifacts.py::
test_readme_publishes_the_same_null_result_without_inflated_claims
```

Scope inspection found no changes to `api.py`, `service.py`, catalog/runtime/database code or
`data/catalog.json`. The new module imports only Python standard-library modules and Pydantic; the
focused isolation test also rejects network/browser/API/service imports. No hardcoded secret-like
assignment was found in the T2 files.

### Recommended next task

Return RHB-T2 to backend/Phase 2 and make the minimum contract repair:

1. derive required exact-authority coverage from every available variant-defining catalog field and
   add a negative test proving omission of each populated field fails;
2. encode a machine-enforced exact-authority eligibility/classification so staged, family-only,
   Human Knowledge, review-family and resolver/model-derived evidence cannot become canonical truth
   merely by flipping permission flags;
3. apply public-artifact PII checks to all publishable authority/label metadata, with explicit tests;
4. fix the focused test typing and restore strict MyPy; and
5. mark T2 complete only after focused/T1/API regressions and this QA recheck pass.

Do not start RHB-T3, change runtime/API/catalog behavior, or repair the unrelated README in this
task. The existing README measured-artifact mismatch should be handled separately before milestone
G3 closure.

---

## RHB-T2 final recheck

### Verdict: PASS

All four initial blockers are resolved and independently rechecked. Exact authority now derives its
required evidence fields from every populated variant-defining field in the bound catalog record;
all six existing T1 sources carry typed, non-exact authority classifications and cannot be promoted
by changing permission/use fields; public authority/query/label metadata rejects obvious contact
PII; and row-level artifacts cannot claim `aggregate_only`. The focused implementation and tests
also pass strict MyPy.

The previously known README measured-artifact mismatch is fixed with the scoped measured claims
restored. The complete suite now passes, so there is no remaining G2/G3 regression attributable to
RHB-T2.

### Rechecked blocker closure

| Initial blocker | Repair evidence | Result |
|---|---|---|
| Incomplete exact-variant field coverage | `validate_canonical_authority` derives the required set from non-empty `casting`, `release_year`, `series`, `color`, `collector_number`, `series_position`, `edition`, and `identifiers`. Seven current populated fields plus a synthetic populated-edition case each have a negative omission test. | CLOSED |
| Staging/family/Human Knowledge source promotion | `AuthorityEligibility` and `AuthorityEvidenceLevel` are allowlisted. Exact candidates must also be a new explicit `authorized_export`; every existing T1 source is prohibited or synthetic-regression-only. A six-source parametrized test changes approval/use/classification fields and still proves each existing source cannot become exact authority. | CLOSED |
| Public metadata PII | Public query, authority and label validators inspect the relevant author/reviewer, family, reason, source reference and evidence-reference text. Email/phone cases fail while ordinary URI evidence remains valid; local-only label metadata remains permitted. | CLOSED |
| `aggregate_only` disguising row artifacts | Authority, query and label artifacts use `RowPublicationScope`, whose only values are `public` and `local_only`; all three reject `aggregate_only`. | CLOSED |
| Strict MyPy error | Strict MyPy passes over the inventory builder, contract module and both focused test files. | CLOSED |
| README/full-suite regression | README once again carries the exact scoped fixture denominator, full neural comparison metrics, gate results, `winner: null`, limitations and links required by measured-artifact tests. Full pytest is green. | CLOSED |

### Requirement result

| Requirement | Final result |
|---|---|
| RHB-R2 | PASS — use, rights, privacy and public-row permissions fail closed. |
| RHB-R5 | PASS — approved exact authority binds catalog UUID/version/record hash, independent exact-authority source class, resolver-output exclusion, review ordering and all populated variant fields. |
| RHB-R6 | PASS — absent exact truth cannot produce a matched/score-eligible label; held/rejected rows cannot be scored. |
| RHB-R7 | PASS — existing fixture, human-label/alignment, staging and Wiki sources cannot become exact canonical authority by permission/use mutation. |
| RHB-R8 | PASS — versioned labels reject unknown fields and incoherent status/review/hard-negative combinations. |
| RHB-R9 | PASS — matched requires exact UUID/authority; ambiguous/no-match cannot carry canonical identity. |
| RHB-R19 | PASS — complete state, exact order/count, content hash and complete sorted parent checksum set are enforced; inventory regeneration is unchanged. |
| RHB-R21 | PASS for T2 — row publication scope, source redistribution/privacy permission and obvious contact-PII boundaries are executable. |

### Final reproduction and evidence

```text
.venv/bin/python scripts/build_representative_hard_benchmark_source_inventory.py --check
unchanged

.venv/bin/python scripts/build_representative_hard_benchmark_source_inventory.py --check
unchanged

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q \
  tests/evaluation/test_representative_benchmark_contract.py
34 passed in 0.10s

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py
7 passed in 0.22s

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q \
  tests/api tests/integration/test_catalog_service.py tests/test_fixture_data.py \
  tests/unit/test_retrieval_policy.py
66 passed, 1 warning in 4.64s

.venv/bin/ruff check --select F,I \
  scripts/build_representative_hard_benchmark_source_inventory.py \
  src/product_variant_resolver/representative_benchmark.py \
  tests/evaluation/test_representative_benchmark_contract.py \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py
All checks passed!

.venv/bin/ruff format --check \
  scripts/build_representative_hard_benchmark_source_inventory.py \
  src/product_variant_resolver/representative_benchmark.py \
  tests/evaluation/test_representative_benchmark_contract.py \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py
4 files already formatted

.venv/bin/mypy --strict \
  scripts/build_representative_hard_benchmark_source_inventory.py \
  src/product_variant_resolver/representative_benchmark.py \
  tests/evaluation/test_representative_benchmark_contract.py \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py
Success: no issues found in 4 source files

.venv/bin/python -m compileall -q src \
  scripts/build_representative_hard_benchmark_source_inventory.py \
  tests/evaluation/test_representative_benchmark_contract.py \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py
PASS

git diff --check
PASS

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q
1016 passed, 1 warning in 95.08s
```

Scope recheck found no modifications to FastAPI, resolver service, runtime policy, canonical catalog
or database code. The contract module remains free of network/browser/API/service imports and no
hardcoded secret-like assignment was found.

### Gate and next task

RHB-T2 is complete. RHB-T3 is still an unstarted owner-decision Gate: its checkbox remains open and
both `source-approval.md` and `source-decisions.json` are absent. The next task may therefore prepare
the exact source/use/publication decision matrix for owner review, but it must not infer an approval,
collect external data, author benchmark cases, or claim that exact real-variant authority exists.

---

## RHB-T3 initial QA

### Verdict: FAIL

The recorded matrix matches the conservative package that the owner approved: 11 sources × 6 uses
produce 66 explicit cells, with 24 `approved`, 42 `rejected`, and 0 `held`. The current artifact
keeps the 101 human rows and 1,763 workbook rows local-only, restricts workbook fields to the six
approved product fields, preserves only the existing attributed 100-row Wiki derivative, exposes
reviewer identity as `project_owner` role only, rejects every exact-authority use, and sets
`network_collection_authorized=false`. RHB-T4/T5 work has not started.

That correct snapshot is not enough to pass Gate B, however. The artifact is parsed as an
unvalidated `dict`; no strict source-decision contract binds it to the inventoried source revision or
enforces the cross-field publication/privacy rules. The focused tests assert selected values in the
current file, but three deliberately invalid in-memory mutations all remained accepted by every
RHB-T3 test. The Gate is therefore not fail-closed as required by RHB-R2, RHB-R4, and RHB-R21.

### Checked items

- Owner confirmation is recorded as role-only `project_owner` at
  `2026-09-27T01:44:16Z`, after the proposal and before this QA run.
- All six inventory source IDs are present exactly once; five explicitly blocked live-source rows
  cover eBay, Mercari, Facebook Marketplace, Fandom, and every other network source.
- Every source has exactly the six declared use cells and every current cell has an explicit
  `approved` or `rejected` status; there are no blank or implied approvals.
- Human-label, alignment, workbook, Wiki, reviewer-identity, exact-authority, raw-evidence,
  public/private, and no-new-network-collection boundaries were compared with the owner's approved
  proposal and the Gate B design.
- T1/T2/T3 focused tests, API/catalog regression, full test suite, JSON parsing, Ruff lint, Ruff
  format, strict MyPy, compileall, diff whitespace, hardcoded-secret scan, and network-client import
  scope were checked.

### Findings

#### Blocker

1. **The source-decision Gate is not fail-closed.** There is no strict schema or validator for
   `source-decisions.json`, and no checksum binds it to `source-inventory.json`. The production
   benchmark validators still consume the T1 inventory whose owner/prospective-use fields remain
   pending; they do not consume this confirmed decision overlay. Current tests accepted all three
   of these invalid mutations: an unknown top-level field, `seller_email` added to the human public
   artifact allowlist, and a rejected exact-authority cell changed to `public_rows` with raw evidence
   allowed. A future edit can therefore widen publication/privacy boundaries while the RHB-T3 tests
   remain green.

#### Important

1. `ruff format --check` fails on
   `tests/evaluation/test_representative_benchmark_source_decisions.py`. The test is typed and lint
   clean, but the task cannot be called repository-clean while its own focused file is unformatted.
2. `data/evaluation/representative-hard-benchmark-v1/README.md` still says only T1/T2 exist, T3 has
   not happened, and the source Gate is pending. That is now stale and contradicts the confirmed
   decision package.

#### Later

- None. RHB-T4 is the next planned task only after this RHB-T3 repair passes QA; its lack of exact
  authority is an expected Gate-C question, not a reason to weaken the T3 source boundaries.

### Reproduction and evidence

```text
jq empty data/evaluation/representative-hard-benchmark-v1/source-decisions.json
PASS

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py \
  tests/evaluation/test_representative_benchmark_contract.py \
  tests/evaluation/test_representative_benchmark_source_decisions.py
44 passed in 0.28s

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q \
  tests/api tests/integration/test_catalog_service.py tests/test_fixture_data.py \
  tests/unit/test_retrieval_policy.py
66 passed, 1 warning in 4.62s

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q
1019 passed, 1 warning in 95.25s

.venv/bin/ruff check --select F,I <RHB-T1/T2/T3 focused files>
All checks passed!

.venv/bin/ruff format --check <RHB-T1/T2/T3 focused files>
FAIL: tests/evaluation/test_representative_benchmark_source_decisions.py would be reformatted

.venv/bin/mypy --strict <RHB-T1/T2/T3 focused files>
Success: no issues found in 5 source files

.venv/bin/python -m compileall -q src <RHB-T1/T2/T3 focused files>
PASS

git diff --check
PASS

QA mutation probe against all three current RHB-T3 tests:
ACCEPTED_BY_CURRENT_TESTS: unknown top-level field
ACCEPTED_BY_CURRENT_TESTS: PII field added to public aggregate contract
ACCEPTED_BY_CURRENT_TESTS: rejected exact-authority cell made row-public
```

No external collection occurred, no runtime/API/catalog/database code changed, and no obvious
hardcoded secret or real reviewer contact information was found. The timestamp-like values found by
the broad contact scan are the expected UTC approval timestamps, not phone numbers.

### Required Phase 2 repair and recommended next task

Return RHB-T3 to `task_executor` before starting RHB-T4:

1. add a strict, unknown-field-rejecting source-decision schema/validator with coherent status,
   publication scope, allowed-field, confirmation, identity, exact-authority, and network rules;
2. bind the decision artifact to the exact source-inventory checksum/version and make the approved
   decision overlay usable by downstream benchmark validation without mutating T1 history;
3. add negative tests for every restricted source class and publication/privacy boundary, including
   the three QA mutations above;
4. format the focused test and refresh the benchmark data README to distinguish completed T3 from
   still-blocked T4/T5; and
5. leave the T3 checkbox/Gate verdict unconfirmed until focused tests, full regression, format,
   strict typing, deterministic checksum checks, and this QA recheck all pass.

---

## RHB-T3 final recheck 1

### Verdict: FAIL

The Phase 2 repair closes the initial artifact-level defects. `SourceDecisionArtifact` and its nested
models now reject unknown fields, bind inventory version/SHA/IDs/authority eligibility, require a
unique complete 11 × 6 matrix, prohibit held cells in a passed Gate, and enforce the current owner
package's major status/scope/field boundaries. The benchmark data README is current, the focused
test is formatted, and all requested static and regression commands pass.

The Gate still fails because downstream enforcement is optional and incomplete. All three public
validation functions accept `source_decisions=None`; a caller can therefore supply a separately
valid but widened inventory and completely omit the owner-confirmed overlay. Independent QA probes
used that path to publish a human query/label with non-role identities and to promote that same
owner-rejected human source into exact canonical authority. Passing the overlay does not fully solve
the problem: the Wiki approval's existing-revision/no-label-truth conditions and the workbook's
family-context-only condition are stored as free-form strings but not enforced by query/label
validation.

### Rechecked blocker closure

| Initial finding | Recheck result |
|---|---|
| Unknown top-level field accepted | CLOSED — strict Pydantic contract rejects it. |
| `seller_email` accepted in public aggregate allowlist | CLOSED — field/scope privacy rules reject it. |
| Rejected exact cell changed to public/raw | CLOSED — rejected/held cells must be prohibited and field-empty. |
| Stale inventory relationship | PARTIAL — direct T3 validation rejects stale SHA/version/IDs/authority eligibility, but downstream functions can omit the overlay entirely. |
| Missing/duplicate use and scope escalation | CLOSED — complete unique use-set and owner-package scope rules reject them. |
| Focused test formatting | CLOSED — touched-surface Ruff format passes. |
| Stale benchmark data README | CLOSED — it now identifies T3 as owner-confirmed and T4/T5 as unstarted. |
| Downstream source boundary | OPEN — optional overlay and unenforced source conditions permit authority/query/label/publication bypasses. |

### Checked items

- Strict extra-forbid behavior and the seven required artifact mutations: unknown top-level field,
  public `seller_email`, rejected exact→public/raw, stale checksum, missing use, duplicate use, and
  human query scope escalation.
- Inventory version, checksum, exact inventory ID set, authority-eligibility equality, five blocked
  external IDs, 11 sources, six unique uses each, 66 total cells, 24 approved, 42 rejected, and zero
  held cells.
- Human/workbook local/public boundaries, Wiki revision/attribution/no-new-collection boundary,
  role-only reviewer identity, exact-authority denial, and network/source rejection.
- Downstream canonical-authority, query-pack, label, reviewer identity, row-publication, and
  family-context behavior both with and without the decision overlay.
- JSON parsing, deterministic inventory rebuild, focused T1–T3 tests, API/catalog regression, full
  suite, touched-surface Ruff lint/format, strict MyPy, compileall, and diff whitespace.
- T4/T5 artifacts remain absent and their task checkboxes remain open.

### Findings

#### Blocker

1. **The confirmed source-decision overlay can be omitted downstream.**
   `validate_canonical_authority`, `validate_query_pack`, and `validate_labels` all default
   `source_decisions` to `None`, falling back to mutable inventory flags or no source-permission
   check. A QA probe changed the human source inventory to a schema-valid approved/public source,
   omitted the overlay, and successfully produced a public query and public ambiguous label with
   `authored_by`/`reviewed_by = not-project-owner`. A second probe changed the same source into a
   schema-valid exact candidate, omitted the overlay, and successfully created
   `approved_exact` authority despite the T3 decision explicitly rejecting that use. This defeats
   RHB-R2, RHB-R4, RHB-R7, and RHB-R21.
2. **Owner-approved context restrictions are not executable downstream.** With the valid overlay
   supplied, an arbitrary `source_record_ref = brand-new-unbound-row` under the Wiki source passed
   as a public query and then as a public, score-eligible ambiguous label. This bypasses
   `existing_checked_in_100_rows_only`, revision binding, and `no_canonical_or_label_truth`.
   Separately, a workbook `family_context_only` row passed as a local, score-eligible `no_match`
   label. The validators check broad use/scope cells but do not check whether the referenced row is
   in the approved revision/manifest or whether a context-only source may establish an outcome
   label.

#### Important

1. `tasks.md` marks RHB-T3 complete even though this final QA recheck is FAIL. The checkbox and
   milestone status must remain open until both downstream blockers are repaired and rechecked.

#### Later

- None. T4/T5 correctly remain unstarted; do not begin either while T3 can be bypassed.

### Independent mutation and bypass evidence

```text
Artifact mutation probe through validate_source_decisions:
REJECTED: unknown_top ValidationError
REJECTED: seller_email ValidationError
REJECTED: exact_public_raw ValidationError
REJECTED: stale_checksum ContractError
REJECTED: missing_use ValidationError
REJECTED: duplicate_use ValidationError
REJECTED: scope_escalation ContractError

Downstream QA probes not covered by the focused suite:
ACCEPTED: omitted optional overlay -> public human query+label and non-role identities
ACCEPTED: omitted optional overlay -> owner-rejected human source became exact authority
ACCEPTED: new unbound Wiki row + public label truth
ACCEPTED: workbook family_context_only became score-eligible no_match label
```

### Regression and static evidence

```text
jq empty data/evaluation/representative-hard-benchmark-v1/source-decisions.json
PASS

.venv/bin/python scripts/build_representative_hard_benchmark_source_inventory.py --check
unchanged

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py \
  tests/evaluation/test_representative_benchmark_contract.py \
  tests/evaluation/test_representative_benchmark_source_decisions.py
54 passed in 0.35s

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q \
  tests/api tests/integration/test_catalog_service.py tests/test_fixture_data.py \
  tests/unit/test_retrieval_policy.py
66 passed, 1 warning in 4.61s

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q
1029 passed, 1 warning in 94.86s

.venv/bin/ruff check --select F,I <RHB-T1/T2/T3 touched Python files>
All checks passed!

.venv/bin/ruff format --check <RHB-T1/T2/T3 touched Python files>
5 files already formatted

.venv/bin/mypy --strict <RHB-T1/T2/T3 touched Python files>
Success: no issues found in 5 source files

.venv/bin/python -m compileall -q src <RHB-T1/T2/T3 touched Python files>
PASS

git diff --check
PASS
```

No network/browser client was added and no T4 authority, query-pack, or label artifact exists. The
only full-suite warning is the pre-existing Starlette `BlockingPortal` deprecation warning.

### Required Phase 2 repair and recommended next task

Return RHB-T3 to `task_executor` again:

1. make the owner-confirmed decision overlay mandatory for every T3+ authority/query/label entry
   point; if T2 compatibility is required, expose explicitly named legacy contract-only helpers
   rather than a silent `None` fallback;
2. bind Wiki query references to the exact approved existing 100-row revision/manifest and prohibit
   Wiki-derived labels, while keeping the approved attribution/query/context use;
3. prohibit workbook/context-only sources from establishing `matched`, `ambiguous`, or `no_match`
   labels, and encode such capabilities as typed policy rather than free-form conditions;
4. add negative tests reproducing all four accepted QA bypasses above; and
5. reopen T3 until focused/full tests and a second final QA recheck pass.

---

## RHB-T3 final recheck 2

### Verdict: FAIL

The second Phase 2 repair closes both bypasses recorded in final recheck 1 at the direct high-level
entry points. `source_decisions` is now a required argument for canonical, query, and label
validation; labels also require the bound inventory; mutable inventory elevation fails the checksum
and authority binding; and typed downstream permissions now distinguish human queries/limited
labels, workbook/alignment family context, revision-bound Wiki queries/context, fixture regression,
and blocked external sources. The owner matrix is internally consistent at 23 approved / 43
rejected / 0 held, with scope counts 10 local-only / 3 aggregate-only / 10 public rows / 43
prohibited.

One composition bypass remains. `validate_labels` accepts a preconstructed `QueryPack` object but
does not re-run `validate_query_pack` against the same inventory and source decisions. Because
Pydantic model construction validates shape rather than owner permissions, QA constructed a public
human query with a private row reference and `authored_by=not-project-owner`, then successfully used
it as the query input for a local, score-eligible ambiguous label. The label reviewer itself was
role-only, but the label entry point still accepted an upstream query that violates the human
local-only and author-identity contract. Thus the combined label flow is not yet fail-closed.

### Rechecked closure

| Final recheck 1 blocker | Final recheck 2 result |
|---|---|
| Decision overlay optional on canonical/query/label validators | CLOSED — all three signatures require `source_decisions`; labels additionally require `inventory`. |
| Mutable inventory can replace the owner overlay | CLOSED at direct entry points — exact inventory checksum/version/IDs/eligibility are rechecked downstream. |
| Non-role query/label/authority identities | CLOSED at direct validators — `project_owner` is required for query author and label/authority reviewer. |
| Arbitrary Wiki record reference | CLOSED at direct query validation — source file checksum, 100-row count, revision 790665, unique IDs, and exact membership are bound. |
| Wiki/workbook context can create scored labels | CLOSED at direct label validation — neither source has `scored_labels`; workbook also lacks `query_pack`. |
| Label validator trusts an unvalidated upstream QueryPack | **OPEN** — shape-valid but permission-invalid human QueryPack is accepted. |

### Checked items

- Re-ran all prior artifact mutations: unknown top-level field, public `seller_email`, rejected
  exact→public/raw, stale inventory checksum, missing use, duplicate use, and scope escalation.
- Confirmed the three high-level signatures make owner-confirmed decisions mandatory and label
  validation also makes inventory mandatory.
- Exercised mutable inventory elevation, role-only author/reviewer enforcement, human local
  ambiguous/no-match versus matched/public restrictions, workbook family-context restrictions,
  Wiki exact-membership and no-label boundary, fixture regression-only boundary, blocked external
  sources, and current exact-authority rejection.
- Verified the final 11 × 6 matrix: 66 unique cells, 23 approved, 43 rejected, 0 held; scopes are 10
  local-only, 3 aggregate-only, 10 public rows, and 43 prohibited.
- Checked README/source approval/tasks consistency. T4/T5 checkboxes remain open and their authority,
  query-pack, and label artifacts are absent.
- Ran JSON parsing, deterministic inventory check, focused T1–T3 tests, API/catalog regression, full
  suite, touched-surface Ruff lint/format, strict MyPy, compileall, and diff whitespace.

### Findings

#### Blocker

1. **`validate_labels` does not validate the supplied QueryPack's owner permissions.** The function
   verifies label-source equality and label-source permissions, but it trusts any `QueryPack`
   instance. Independent reproduction used `QueryPack.model_validate` to create:
   `publication_scope=public`, `source_id=human-labeled-real-noisy-v1`,
   `source_record_ref=private-row`, and `authored_by=not-project-owner`. Passing that object into
   `validate_labels` with a valid bound inventory/decision overlay and a local ambiguous label
   returned successfully. This bypasses the typed human `local query only` rule and role-only query
   author rule through the high-level label flow, violating RHB-R2, RHB-R4, and RHB-R21.

#### Important

1. `tasks.md` still marks RHB-T3 complete. Because final recheck 2 is FAIL, the task status remains
   premature until the composition bypass is repaired and rechecked.

#### Later

- None. T4/T5 correctly have no artifacts yet and must remain unstarted.

### Mutation and bypass evidence

```text
Artifact mutation probe through validate_source_decisions:
REJECTED: unknown_top ValidationError
REJECTED: seller_email ValidationError
REJECTED: exact_public_raw ValidationError
REJECTED: stale_checksum ContractError
REJECTED: missing_use ValidationError
REJECTED: duplicate_use ValidationError
REJECTED: scope_escalation ContractError

Final composition probe:
ACCEPTED: labels accepted unvalidated public human query authored by non-role identity
```

The direct negative tests for omitted decisions, mutable inventory, non-role identities, arbitrary
Wiki references, Wiki labels, workbook labels, fixture query escalation, human public/matched labels,
blocked external sources, and exact authority all pass. The remaining failure is specifically the
composition boundary where a low-level-constructed QueryPack is supplied to label validation.

### Regression and static evidence

```text
jq empty data/evaluation/representative-hard-benchmark-v1/source-decisions.json
PASS

.venv/bin/python scripts/build_representative_hard_benchmark_source_inventory.py --check
unchanged

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py \
  tests/evaluation/test_representative_benchmark_contract.py \
  tests/evaluation/test_representative_benchmark_source_decisions.py
66 passed in 0.37s

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q \
  tests/api tests/integration/test_catalog_service.py tests/test_fixture_data.py \
  tests/unit/test_retrieval_policy.py
66 passed, 1 warning in 4.93s

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q
1041 passed, 1 warning in 96.66s

.venv/bin/ruff check --select F,I <RHB-T1/T2/T3 touched Python files>
All checks passed!

.venv/bin/ruff format --check <RHB-T1/T2/T3 touched Python files>
5 files already formatted

.venv/bin/mypy --strict <RHB-T1/T2/T3 touched Python files>
Success: no issues found in 5 source files

.venv/bin/python -m compileall -q src <RHB-T1/T2/T3 touched Python files>
PASS

git diff --check
PASS
```

The touched-surface checks are clean. No claim is made about a separate whole-repository Ruff/MyPy
baseline; the full behavior suite is green apart from the pre-existing Starlette
`BlockingPortal` deprecation warning.

### Required Phase 2 repair and recommended next task

Return RHB-T3 to `task_executor` once more:

1. at the start of `validate_labels`, revalidate the supplied query pack against the same bound
   inventory and owner decisions—for example, by feeding a JSON-mode dump through
   `validate_query_pack`—or require an unforgeable validated-query wrapper;
2. add a negative test with a low-level-constructed public human QueryPack containing a private
   source reference and non-role author, proving label validation rejects it;
3. also revalidate any upstream authority artifact before a future decision version permits matched
   labels, so the same composition weakness is not deferred into T4/T6; and
4. reopen T3 until focused/full checks and final recheck 3 pass.

---

## RHB-T3 final recheck 3

### Verdict: PASS

The final composition blocker is closed. `validate_labels` now serializes and revalidates both the
consumed `QueryPack` and `CanonicalAuthorityArtifact` through their high-level validators using the
same checksum-bound inventory and owner-confirmed source decisions before any label join. A caller
can no longer bypass T3 by constructing a shape-valid model directly or by mutating a nested author
or reviewer after an earlier successful validation.

The final decision package remains exactly the owner-approved conservative boundary: 11 sources ×
6 uses = 66 unique cells, with 23 approved, 43 rejected, and 0 held; publication scopes are 10
local-only, 3 aggregate-only, 10 public rows, and 43 prohibited. T4/T5 have not started.

### Final blocker closure

| Final recheck 2 blocker | Final result |
|---|---|
| Preconstructed public human QueryPack bypasses label flow | CLOSED — label validation re-runs query validation and rejects human `public_rows`. |
| Nested query author changed after validation | CLOSED — JSON serialization plus revalidation rejects any author other than role-only `project_owner`. |
| Nested authority reviewer changed after validation | CLOSED — consumed authority is revalidated and rejects any reviewer other than role-only `project_owner`. |
| Future matched-label authority composition risk | CLOSED for the current contract — label validation revalidates the full consumed authority artifact before UUID/authority joins. |

### Checked items

- Reproduced the prior public-human/private-ref/non-project-owner preconstructed QueryPack attack;
  it now fails at the human query publication scope.
- Reproduced nested mutation of a previously validated query's `authored_by`; it now fails the
  role-only author check.
- Reproduced nested mutation of a previously validated authority record's `reviewed_by`; it now
  fails the role-only authority-reviewer check.
- Re-ran every earlier source-decision mutation: unknown field, public `seller_email`, rejected
  exact→public/raw, stale inventory checksum, missing use, duplicate use, and scope escalation.
- Reconfirmed mandatory decision/inventory arguments, mutable inventory rejection, human
  local-query and ambiguous/no-match-only policy, workbook/alignment context-only policy, exact
  checksum/revision membership for Wiki query references, no Wiki/workbook labels, fixture
  regression-only behavior, blocked external sources, and rejection of exact authority for every
  current source.
- Confirmed README, source approval, decision JSON, and task status agree. T4/T5 task checkboxes are
  open; canonical-authority, query-pack, and label artifacts are absent.
- Ran focused T1–T3 tests, API/catalog regression, full suite, touched-surface Ruff lint/format,
  strict MyPy, compileall, deterministic inventory check, JSON parse, and diff whitespace.

### Findings

#### Blocker

- None.

#### Important

- None for RHB-T3.

#### Later

- The Starlette `BlockingPortal` deprecation warning remains an existing dependency warning; it does
  not affect the benchmark source Gate.
- Exact real-variant authority remains intentionally absent. This is the subject of RHB-T4 and must
  not be inferred from the RHB-T3 PASS.

### Independent attack evidence

```text
REJECTED: preconstructed public human query ContractError
source 'human-labeled-real-noisy-v1'/query_text cannot satisfy public_rows scope

REJECTED: nested author mutation ContractError
queries must use role-only author project_owner

REJECTED: nested authority reviewer mutation ContractError
authority reviews must use role-only reviewer project_owner

Artifact mutation probe through validate_source_decisions:
REJECTED: unknown_top ValidationError
REJECTED: seller_email ValidationError
REJECTED: exact_public_raw ValidationError
REJECTED: stale_checksum ContractError
REJECTED: missing_use ValidationError
REJECTED: duplicate_use ValidationError
REJECTED: scope_escalation ContractError
```

### Final regression and static evidence

```text
jq empty data/evaluation/representative-hard-benchmark-v1/source-decisions.json
PASS

.venv/bin/python scripts/build_representative_hard_benchmark_source_inventory.py --check
unchanged

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py \
  tests/evaluation/test_representative_benchmark_contract.py \
  tests/evaluation/test_representative_benchmark_source_decisions.py
69 passed in 0.33s

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q \
  tests/api tests/integration/test_catalog_service.py tests/test_fixture_data.py \
  tests/unit/test_retrieval_policy.py
66 passed, 1 warning in 4.55s

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q
1044 passed, 1 warning in 94.92s

.venv/bin/ruff check --select F,I <RHB-T1/T2/T3 touched Python files>
All checks passed!

.venv/bin/ruff format --check <RHB-T1/T2/T3 touched Python files>
5 files already formatted

.venv/bin/mypy --strict <RHB-T1/T2/T3 touched Python files>
Success: no issues found in 5 source files

.venv/bin/python -m compileall -q src <RHB-T1/T2/T3 touched Python files>
PASS

git diff --check
PASS
```

These Ruff/MyPy results cover the files touched by RHB-T1–T3. They do not claim a separate clean
whole-repository Ruff/MyPy baseline. The full behavior suite is green.

### Gate and recommended next task

RHB-T3 is complete for the explicitly approved scopes. This PASS authorizes only the next independent
task, **RHB-T4 catalog-ground-truth eligibility audit**. It does not authorize network collection,
new Wiki rows, query-pack or label authoring, T5, or canonical promotion. If RHB-T4 finds fewer than
20 independently supported exact variants or fewer than four same-casting multi-release families,
the matched pilot must stop at that documented shortfall.

---

## RHB-T4 final QA

### Verdict: PASS (engineering) / DATA GATE BLOCKED

The RHB-T4 implementation is deterministic, fail-closed and independently reproducible. It audits
the frozen catalog, Human-backed catalog, T1 source inventory and T3 owner decisions without using
network access, resolver output or benchmark labels. The empty `authority_records` result is derived
from every current source and both catalog surfaces; it is not an omitted scan or a silently empty
builder result.

The data Gate deliberately does **not** pass. The audit finds `0` eligible exact variants, `0`
pilot-usable exact variants and `0` eligible same-casting/multi-release families. Against the
predeclared minimums, the shortfall is `20` variants and `4` families, so the machine-readable result
is `blocked_insufficient_exact_authority`. RHB-T5 and every query/label/matched-pilot or UUID-inference
step remain prohibited until a newly authorized exact-variant source passes both a new T3-style
source decision and this authority audit.

### Checked items

- Frozen `fixture-v1` catalog: exactly 120 products; every provenance item is
  `synthetic_fixture` with a `synthetic://fixture-v1/` reference; all 120 are excluded as
  regression-only and none counts as real exact authority.
- Human-backed catalog: exactly 97 castings and 100 provisional variants; every provisional variant
  remains `needs_canonical_review`, no provisional row contains a canonical UUID, exact count is
  zero, and `canonical_variant_response` remains explicitly excluded.
- T1/T3 parents: inventory and manifest revalidate; all 11 owner-confirmed source/use cells for
  `exact_variant_authority` are rejected; no source has typed `canonical_authority` downstream
  permission.
- Empty canonical authority: `records=[]`, record order is empty and stable, artifact SHA/version
  bind to the manifest, and the eligible/usable/family counts all equal zero.
- Threshold/Gate arithmetic: minimums `20` and `4`, observed values `0` and `0`, shortfalls `20` and
  `4`, Gate result `blocked_insufficient_exact_authority`, and the only permitted next step is to
  obtain newly authorized exact-variant evidence.
- Manifest stability: schema/version/status, sorted parent paths and SHA-256 values, catalog and
  product counts/checksums, Human catalog counts/checksum, source ordering/counts and generated
  metadata all validate. T1 and T4 builders return `unchanged`; the T4 check succeeds twice.
- Negative mutations: stale authority SHA, stale parent SHA, partial status, unknown field, source
  count mismatch, source-order mismatch, exact-authority decision elevation, a fabricated non-empty
  fixture authority record, stale catalog-record checksum, missing populated variant-field coverage,
  wrong reviewer role, timezone-naive review time, empty independent evidence, and
  `resolver_output_consulted=true` are all rejected.
- Scope boundary: no network/browser/resolver/model/runtime/API/catalog/database behavior is added;
  no benchmark query pack, label, held-label, split, raw Test or scored-evaluation artifact exists.
- T4 is recorded as `COMPLETE — GATE BLOCKED`; RHB-T5 and all later task checkboxes remain open.
- Focused T1–T4, API/catalog regression, full pytest, Ruff, format, strict MyPy, compileall, T1/T4
  deterministic checks, JSON parsing, secret scan and `git diff --check`.

### Requirement coverage

| Requirement | Evidence | Result |
|---|---|---|
| RHB-R5 | Authority records are checked against canonical catalog version, UUID, product-record checksum, independently authorized source, populated variant fields, reviewer and aware timestamp. Current records are empty because no existing source satisfies those preconditions. | PASS |
| RHB-R6 | No expected UUID or matched label is authored. Exact truth absence produces a blocked Gate and explicit downstream prohibitions instead of an inferred nearest UUID. | PASS |
| RHB-R7 | Synthetic fixture, Human Knowledge, family alignment, owner staging and Wiki data are all rejected as exact authority; mutation cannot elevate the T3 decision. | PASS |
| RHB-R9 | No outcome label is created in T4. The existing contract still requires independently approved exact authority before any future `matched` label. | PASS |
| RHB-R19 | Artifact/parent hashes, counts, stable ordering, versions and generation metadata are frozen; stale, partial, reordered, count-inconsistent and unknown-field mutations fail closed; repeated checks return `unchanged`. | PASS |
| RHB-R21 | Public T4 artifacts contain schemas, role-safe summaries, aggregate counts and non-sensitive checksums only; no local row evidence or personal contact data is copied. | PASS |

### Findings

#### Blocker

- None in the RHB-T4 implementation.

#### Important

- `docs/evidence/representative-hard-benchmark-authority-audit.md`, listed in the T4 task, is not yet
  present. The doc curator must add the narrative evidence before this task is committed as a fully
  documented Lean milestone. This does not change the independently verified engineering PASS or
  the blocked data Gate.

#### Later

- The existing Starlette `BlockingPortal` deprecation warning remains dependency debt; it does not
  affect the offline authority audit.
- `0` eligible exact variants is not resolver-quality evidence and must not be reframed as an
  accuracy result. It means the project lacks lawful, independently reviewed release-level truth.
- RHB-T5 must remain unstarted. New evidence requires an explicit source-decision update and a fresh
  authority audit; family labels, staged variants, Wiki rows, synthetic UUIDs and resolver candidates
  cannot fill the shortfall.

### Reproduction and evidence

```text
.venv/bin/python scripts/build_representative_hard_benchmark_source_inventory.py --check
unchanged

.venv/bin/python scripts/build_representative_hard_benchmark_canonical_authority.py --check
unchanged

.venv/bin/python scripts/build_representative_hard_benchmark_canonical_authority.py --check
unchanged

.venv/bin/pytest --override-ini addopts='' -q \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py \
  tests/evaluation/test_representative_benchmark_contract.py \
  tests/evaluation/test_representative_benchmark_source_decisions.py \
  tests/evaluation/test_representative_benchmark_canonical_authority_audit.py
76 passed in 0.61s

.venv/bin/pytest --override-ini addopts='' -q \
  tests/api/test_api.py tests/integration/test_catalog_service.py \
  tests/test_fandom_catalog_review.py tests/test_human_backed_catalog.py \
  tests/test_human_catalog_alignment.py tests/test_real_catalog_source_expansion_plan.py
57 passed, 1 warning in 0.92s

.venv/bin/pytest --override-ini addopts='' -q
1051 passed, 1 warning in 95.60s

.venv/bin/ruff check \
  src/product_variant_resolver/representative_benchmark.py \
  scripts/build_representative_hard_benchmark_canonical_authority.py \
  tests/evaluation/test_representative_benchmark_canonical_authority_audit.py
All checks passed!

.venv/bin/ruff format --check <same three touched Python files>
3 files already formatted

.venv/bin/mypy --strict <same three touched Python files>
Success: no issues found in 3 source files

.venv/bin/python -m compileall -q <same three touched Python files>
PASS

jq -e . canonical-authority.json canonical-authority-manifest.json
PASS

git diff --check
PASS
```

Independent frozen-data inspection:

```text
fixture-v1: 120 products; all synthetic regression-only
human-backed-catalog-v1: 97 castings; 100 provisional; 0 exact
T3 decisions: 11 exact-authority cells; 11 rejected; 0 canonical permissions
canonical authority records: 0
eligible / pilot-usable / same-casting-multi-release families: 0 / 0 / 0
shortfall: 20 variants / 4 families
gate: blocked_insufficient_exact_authority
network / resolver output / benchmark labels consulted: 0 / false / false
```

### Recommended next task

Send the verified T4 result to `doc_curator` to create
`docs/evidence/representative-hard-benchmark-authority-audit.md` and append the narrative Project Log
entry. Do not start RHB-T5. After documentation, commit the isolated RHB-T4 checkpoint and request
explicit approval before pushing it to GitHub. The next product decision is how to obtain a lawful,
independently reviewed exact-variant authority source; without that new evidence, the benchmark must
remain stopped at this Gate.
