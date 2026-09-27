# Representative Hard Benchmark v1 — Lean QA Review

Date: 2026-09-26. Mode: Lite / Lean Industrial. Scope: **RHB-T1 recheck 2 + RHB-T2 initial QA**.

## Current milestone verdict: PASS

RHB-T1 remains PASS. RHB-T2 passed its final recheck after the Phase 2 repair documented at the end
of this review. The initial RHB-T2 FAIL and its reproduction evidence are retained below as QA
history; the final recheck supersedes that earlier verdict. RHB-T3 has not started.

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
