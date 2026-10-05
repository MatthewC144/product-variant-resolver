# Canonical Authority Review v1 — Lean QA Review

## Current milestone verdict — PASS / DATA GATE PASS / RHB-T5 UNAUTHORIZED

Date: 2026-10-04. Mode: Lite / Lean Industrial. Scope: **CAR-T1–T7 final closure**.

### Outcome

Canonical Authority Review v1 passes its engineering and data Gates. The completed workflow used
only the approved frozen community snapshot, remained output-blind and offline, created 20 distinct
`approved_exact` variants across seven qualifying multi-release families, and recorded zero
shortfalls. The separately authorized CAR-T6 re-audit therefore reports
`passed_exact_authority_gate`.

This PASS is exact relative to `List of 2025 Hot Wheels` revision `790665`; it is not
Mattel/manufacturer-certified truth. Color and edition remain null. The historical zero-record
RHB-T4 blocked audit remains valid, byte-preserved history; the new PASS is a separate versioned
result based on later evidence. RHB-T5, query-pack authoring and label authoring remain unauthorized.

### Requirement coverage

| Requirement | Primary implementation/evidence | Verification | Result |
|---|---|---|---|
| CAR-R1 | Source decision, frozen revision/row/license bindings, `canonical_authority_source_gate.py` | Source Gate CLI valid; 41 source-decision tests within focused suite | PASS |
| CAR-R2 | Candidate, catalog proposal/application and exact field-evidence contracts | Catalog/application/review tests reject context-to-truth promotion; color/edition stay null | PASS |
| CAR-R3 | Private output-blind packet plus safe manifest | Preparation/packet tests; resolver output flags false; private paths ignored | PASS |
| CAR-R4 | Append-only T5-G1/T5-G2 events and owner attestations | Decision suites validate staged→reviewed→approved transitions and distinct owner Gates | PASS |
| CAR-R5 | Held/conflicted/insufficient and stale/blindness rejection | Negative transition, evidence, stale-hash and output-consultation cases pass | PASS |
| CAR-R6 | Git-safe public metadata and ignored `0600` private ledgers | Public owner-response scan zero; source/packet/publication/PII validators pass | PASS |
| CAR-R7 | Canonical JSON, hashes, atomic writes, rollback and replay | CAR-T6 and historical audit checks return `unchanged`; injected-write tests pass | PASS |
| CAR-R8 | Distinct exact count and multi-release family threshold | 20 unique UUIDs, seven qualifying families, zero shortfalls | PASS |
| CAR-R9 | Versioned RHB-T4 handoff preserving old audit | New re-audit PASS beside unchanged historical blocked files; RHB-T5 false | PASS |
| CAR-R10 | Positive and adversarial regression | 317 focused tests and 1,379 full-repository tests pass | PASS |
| CAR-R11 | QA matrix, deterministic evidence, AI eval and narrative log | This review plus final evidence, AI rubric, Portfolio Guide and Project Log | PASS |

### Verification evidence

- Authority/CAR-T6/historical RHB-T4 focused suite: **317 passed**.
- Full repository suite on the final code/data tree before documentation-only CAR-T7 edits:
  **1,379 passed, 1 pre-existing Starlette/AnyIO deprecation warning**.
- CAR-T1 Source Gate: `valid`.
- CAR-T6 re-audit check: `unchanged`; historical RHB-T4 check: `unchanged`.
- Ruff check: PASS; Ruff format check: 20 files already formatted.
- Strict MyPy on the nine production/CLI modules plus the CAR-T6 test: **10 files, no issues**.
- Python compileall, six critical JSON parses and `git diff --check`: PASS.
- Private authorization remains Git-ignored; the actual owner response has zero hits outside the
  private directory. Public authority/manifest modes are `0644`; private authorization is `0600`.
- Resolver output consulted, benchmark labels consulted and network requests are all zero.

An intentionally broader strict-MyPy diagnostic over all legacy authority tests found 22 existing
test-only issues in three modules: internal-module attribute access and string indexing of
enum-keyed dictionaries. Runtime behavior is covered by the 317 passing focused tests, and all
production modules plus the newly added CAR-T6 test pass strict MyPy. This is recorded as test-type
debt rather than misreported as a repository-wide strict pass.

### Findings

#### Blocker

- None.

#### Important

- None for CAR v1 closure.

#### Minor / carry-forward

- Clean up the 22 legacy authority-test MyPy diagnostics if tests are later added to a repository-
  wide static-type Gate. They do not affect production artifacts or runtime test results.
- The authority claim is community-revision exact, not manufacturer-certified; unsupported color
  and edition values must not be inferred later.
- RHB-T5 needs a separate owner authorization and output-blind protocol. A passed authority Gate is
  necessary input, not benchmark-readiness or resolver-quality evidence.

### Engineering result versus data result

- **Engineering:** PASS — contracts, state transitions, privacy, atomicity, determinism, historical
  preservation and documentation meet CAR-R1–R11.
- **Data:** PASS — 20 exact variants / seven qualifying families / zero shortfalls at the declared
  community-reference claim tier.
- **Downstream:** CLOSED — RHB-T5/query/label work remains unauthorized.

The sections below retain the original CAR-T1 FAIL and repair PASS as audit history. They are no
longer the current milestone verdict.

---

Date: 2026-09-28. Mode: Lite / Lean Industrial. Scope: **CAR-T1 only**.

## Verdict: FAIL (return to Phase 2)

The checked-in CAR-T1 decision and manifest currently describe the intended Source Gate honestly:
one existing 100-row normalized text derivative may enter later output-blind owner review, while no
canonical UUID, `approved_exact` row, 20/4 composition pass or RHB-T5 authorization exists. The
underlying snapshot also has the claimed 100 unique IDs, 38 multi-release families and 85 rows in
those families.

CAR-T1 cannot pass Lean QA yet because its integrity tests are not fail-closed. In isolated temporary
copies, three prohibited mutations survived all seven CAR-T1 tests after the outer manifest hash was
updated: an unknown decision field, an unknown manifest field, and removal of the required
attribution text. A checksum proves that bytes are internally bound; it does not prove that the
decision has the required schema or licensing content.

## Source Gate scope and remaining data status

- **Source Gate scope:** the intended approval is limited to the already checked-in
  `normalized.json` derivative for `List of 2025 Hot Wheels`, revision `790665`, timestamp
  `2026-07-17T05:50:26Z`. Its maximum claim tier is
  `community_reference_snapshot_exact`, not Mattel/manufacturer-certified truth.
- **License/access boundary:** CC-BY-SA attribution and share-alike are required. The decision does
  not claim that Fandom authorized the historical automated access. New network, browser, API,
  Selenium/crawler, raw-page, image/media and OCR acquisition remain disabled.
- **Review boundary:** the reviewer role is `project_owner`, confirmation is
  `owner_attestation`, and resolver/model output must remain hidden. This approval permits a later
  review; it does not itself approve an authority row.
- **Workbook boundary:** the 1,763-row workbook remains `family_context` /
  `candidate_selection_only`, rejected as exact evidence.
- **Remaining data status:** `approved_exact_count=0`, canonical UUID approvals are zero, the 20
  variants/four families minimum is false, and RHB-T5 remains false. CAR-T2 and later tasks have not
  started.

## Checked items

- Source kind, claim tier, page, revision, revision timestamp, source ID, artifact path and SHA-256.
- Existing normalized derivative only; no new raw page, image/media, OCR, network or browser work.
- Allowed mapping for casting, release year, series, collector number, series position, toy number
  and variant-note context.
- All 100 rows preserve `color=null`; `2nd Color` is not treated as a color value. Edition remains
  absent and is not inferred.
- CC-BY-SA license URL, attribution/share-alike intent and row-binding requirements.
- `project_owner`/`owner_attestation`, output blindness, default hold policy for new sources and
  workbook exact-authority rejection.
- Source Gate approval versus authority approval, canonical UUID approval, 20/4 composition and
  RHB-T5 authorization.
- 100 IDs are unique and have the declared canonical-set SHA-256; page/revision/source metadata is
  consistent across current rows.
- Candidate feasibility: 100 rows, 38 multi-release families, 85 rows in those families; missing
  counts are zero for all six key fields, 100 for color and 100 for edition. These are feasibility
  only.
- Focused CAR/RHB regression, full pytest, Ruff, format, strict MyPy, compileall, JSON parsing and
  `git diff --check`.
- Isolated negative mutations covering unknown fields, stale decisions/normalized/source-manifest
  and ID-set hashes, page/revision/source mismatches, duplicate/missing IDs, license/share-alike,
  manufacturer escalation, network/scraping flags, historical-access claims, workbook promotion,
  color inference, authority/UUID/20-4/RHB-T5 escalation and partial status.

## Requirement coverage

| Requirement | Evidence | Result |
|---|---|---|
| CAR-R1 | Current content binds the intended snapshot, source/page/revision, access limitation, allowed use and checksum. Unknown decision fields are nevertheless accepted, and required attribution text may be removed after rebinding the checksum. | **FAIL** |
| CAR-R2 | Current content limits fields, leaves color unknown, does not infer edition, and keeps workbook rows context-only. Negative mutations for workbook promotion and color inference are rejected. | PASS for T1 scope |
| CAR-R6 | Current artifacts contain safe role-only metadata and correctly prohibit new raw/image/media acquisition. License/share-alike flags are present, but removal of `attribution_text` is not rejected and the manifest accepts unknown fields. | **FAIL** |

## Findings

### Blocker

1. **Source decision schema is not strict.** Adding an unknown top-level key to
   `source-decisions.json`, then updating its manifest SHA-256, passes all CAR-T1 tests. There is no
   strict parser or exact-key assertion for the source decision. This violates the fail-closed
   decision contract in CAR-R1.

2. **Safe manifest schema is not strict.** Adding an unknown top-level key directly to
   `source-decisions-manifest.json` passes all CAR-T1 tests. The manifest is the verification
   envelope and currently has neither a strict schema nor an exact-key check.

3. **Required attribution can be removed.** Deleting
   `license_and_attribution.attribution_text` and updating the decision binding passes all CAR-T1
   tests. `license_name`, row-binding names and `share_alike_required` are checked, but the actual
   required attribution statement is not. CAR-R1/R6 require attribution, not merely a self-consistent
   checksum.

4. **Some published feasibility facts are not recomputed by the integrity test.** The current
   values are factually correct, but `candidate_feasibility.missing_field_counts` is read without
   assertions. A future drift could misreport the zero-key/100-color/100-edition baseline while the
   suite remains green. CAR-T1's safe planning baseline should be derived from the frozen rows and
   compared exactly.

### Important

- The original artifacts themselves are internally consistent and contain no observed authority
  escalation. The FAIL concerns enforcement: current tests cannot guarantee that a modified copy
  preserves the same contract.
- Hash rebinding must never be treated as approval. Semantic validation must run before or alongside
  checksum validation.

### Later

- Do not start CAR-T2 contracts until these T1 source-decision integrity checks pass independently.
- Passing CAR-T1 will authorize only the next engineering task. It will still leave exact authority
  at zero and will not authorize RHB-T5.

## Reproduction and evidence

Current-artifact checks:

```text
.venv/bin/pytest \
  tests/authority/test_canonical_authority_source_decision.py \
  tests/evaluation/test_representative_benchmark_source_decisions.py \
  tests/evaluation/test_representative_benchmark_canonical_authority_audit.py \
  tests/evaluation/test_representative_benchmark_contract.py \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py
83 passed in 0.54s

.venv/bin/ruff check tests/authority/test_canonical_authority_source_decision.py
All checks passed!

.venv/bin/ruff format --check tests/authority/test_canonical_authority_source_decision.py
1 file already formatted

.venv/bin/mypy --strict tests/authority/test_canonical_authority_source_decision.py
Success: no issues found in 1 source file

.venv/bin/python -m compileall -q \
  tests/authority/test_canonical_authority_source_decision.py
PASS

.venv/bin/pytest
1058 passed, 1 warning in 93.91s

python -m json.tool source-decisions.json / source-decisions-manifest.json /
  normalized.json / source manifest
PASS

git diff --check
PASS
```

Independent source recomputation:

```text
rows=100; unique_ids=100
source_record_ids_sha256=c2412a8e9fa8fe78a2e8f6c932636e5d2a965131f0561843d179d13cdd8adba7
multi_release_families=38; rows_in_multi_release_families=85
missing toy_number/casting/year/series/collector_number/series_position=0
missing color=100; missing edition=100; non-null canonical_uuid=0
```

Isolated mutation result (temporary copies; project artifacts were not edited):

```text
25 mutations attempted
22 rejected
3 incorrectly accepted:
  unknown_decision_field
  unknown_manifest_field
  attribution_removed
```

The rejected set included stale bindings, duplicate/missing IDs, page/revision/source mismatch,
license/share-alike removal, manufacturer claim escalation, network/crawler enablement, false
historical-access approval, workbook exact promotion, color inference, authority/UUID/20-4/RHB-T5
escalation and partial status.

## Recommended next task

Return CAR-T1 to the task executor. Add strict source-decision and manifest validation (or exact-key
integrity assertions), require and verify the attribution text, recompute every published missing
count from the frozen rows, and add regression mutations for all three demonstrated bypasses. Then
rerun this same Lean QA before CAR-T2 begins.

---

## CAR-T1 repair recheck — final verdict: PASS

Date: 2026-09-28. The initial FAIL above is retained as audit history. The repair resolves all four
reported blockers and CAR-T1 now passes Lean QA.

### Engineering verdict: PASS

The dedicated offline validator
`product_variant_resolver.canonical_authority_source_gate` now validates the inner semantics of the
decision, normalized snapshot and frozen source manifest before accepting outer artifact hashes. It
uses exact-key contracts at every object boundary, rejects duplicate JSON keys, binds approved
constants and parent spec bytes, recomputes row membership and feasibility facts, and treats a
self-consistent rehash as insufficient when a semantic boundary changed.

This module remains CAR-T1-only. It does not implement candidates, field-evidence review, catalog
proposals, review events, authority bundles, runtime resolver behavior or any CAR-T2 feature. Its
imports are local/offline standard-library components; it introduces no network, browser, FastAPI,
resolver or database dependency. The CLI succeeds against the current repository:

```text
PYTHONPATH=src .venv/bin/python -m \
  product_variant_resolver.canonical_authority_source_gate --root .
CAR-T1 source Gate: valid
```

### Source Gate scope: PASSED, narrowly

The PASS approves only later output-blind human review of the existing normalized 100-row text
derivative for `List of 2025 Hot Wheels`, revision `790665`, timestamp
`2026-07-17T05:50:26Z`.

- `source_kind=licensed_community_snapshot` and
  `claim_tier=community_reference_snapshot_exact` remain exact only relative to the frozen community
  revision after later owner review; neither is a Mattel/manufacturer certification.
- CC-BY-SA license URL, named contributor attribution, revision attribution, normalized-derivative
  notice, required row bindings and share-alike are mandatory.
- Historical automated-access permission remains unestablished. The decision does not claim Fandom
  approval, and all network/browser/API/crawler/raw-page/image/media/OCR flags remain false or zero.
- Allowed mappings remain limited to the approved fields. All 100 colors remain null, edition is
  absent for all 100 rows, and `2nd Color` cannot infer a color name.
- Public reviewer identity remains `project_owner`, confirmation remains `owner_attestation`, and
  resolver/model output remains forbidden from the review.
- The 1,763-row workbook remains context/candidate-selection-only and cannot establish an exact
  value or UUID. Unknown or future sources remain held pending a separate owner decision.

### Remaining data status: still zero authority

This engineering PASS is not an authority PASS:

- `approved_exact_count=0`
- authority rows created: `0`
- canonical UUID approvals: `0`
- 20 variants/four families minimum: `false`
- RHB-T5 authorization: `false`
- CAR-T2 through CAR-T7: not started

The verified `100 / 38 / 85` figures and missing counts are
`candidate_feasibility_not_authority`; they only show that CAR-T3 may later propose a queue after
CAR-T2 is completed.

### Repair verification

The independent QA harness repeated the previous 25 mutations and added nine adversarial cases.
All 34 were rejected:

```text
previous 25 mutations:                         25/25 rejected
unknown nested decision field:                  rejected
unknown nested manifest field:                  rejected
missing color count 100 -> 99:                  rejected
missing edition count 100 -> 99:                rejected
variant_note missing count 55 -> 54:            rejected
source-manifest revision + self-consistent hash: rejected
normalized semantic drift + all parent rehashes: rejected
duplicate JSON key:                             rejected
bound spec parent drift:                        rejected
SUMMARY: 34/34 rejected
```

This includes the three original bypasses: unknown decision fields, unknown manifest fields and
removed/blank attribution text. It also confirms that outer hash rebinding cannot authorize
manufacturer escalation, exact-authority counts, UUID approval, workbook promotion, network
collection, historical-access claims, inferred color, a 20/4 pass or RHB-T5.

The validator independently recomputed:

```text
rows=100; unique source_record_id values=100
source-record ID set SHA-256=
  c2412a8e9fa8fe78a2e8f6c932636e5d2a965131f0561843d179d13cdd8adba7
multi-release families=38; rows in those families=85
missing toy_number/casting_name/release_year/series/collector_number/series_position=0
missing color=100; missing edition=100; missing variant_note=55
non-null canonical_uuid=0
```

### Final test evidence

```text
.venv/bin/pytest tests/authority/test_canonical_authority_source_decision.py
41 passed in 0.07s

.venv/bin/pytest \
  tests/authority/test_canonical_authority_source_decision.py \
  tests/evaluation/test_representative_benchmark_source_decisions.py \
  tests/evaluation/test_representative_benchmark_canonical_authority_audit.py \
  tests/evaluation/test_representative_benchmark_contract.py \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py
117 passed in 0.59s

.venv/bin/pytest
1092 passed, 1 warning in 95.15s

.venv/bin/ruff check \
  src/product_variant_resolver/canonical_authority_source_gate.py \
  tests/authority/test_canonical_authority_source_decision.py
All checks passed!

.venv/bin/ruff format --check \
  src/product_variant_resolver/canonical_authority_source_gate.py \
  tests/authority/test_canonical_authority_source_decision.py
2 files already formatted

.venv/bin/mypy --strict \
  src/product_variant_resolver/canonical_authority_source_gate.py \
  tests/authority/test_canonical_authority_source_decision.py
Success: no issues found in 2 source files

.venv/bin/python -m compileall -q \
  src/product_variant_resolver/canonical_authority_source_gate.py \
  tests/authority/test_canonical_authority_source_decision.py
PASS

python -m json.tool decisions / decision manifest / normalized snapshot / source manifest
PASS

git diff --check
PASS
```

The single full-suite warning is Starlette's existing `anyio.abc.BlockingPortal` deprecation and is
unrelated to CAR-T1.

### Final findings

#### Blocker

- None.

#### Important

- None for CAR-T1.

#### Later

- Any legitimate future edit to a bound decision, source artifact or spec parent must update the
  versioned manifest deliberately and still pass semantic validation; recomputing a SHA alone is
  not approval.
- CAR-T2 must remain a separate commit and QA scope. It may now implement the broader candidate,
  review-event and authority-bundle contracts, but it still may not create real authority rows.

### Recommended next task

Proceed to **CAR-T2 — Implement strict contracts**. Preserve the Source Gate's offline, output-blind,
context-versus-authority and zero-authority boundaries. Do not begin CAR-T3 candidate selection or
claim benchmark readiness during CAR-T2.
