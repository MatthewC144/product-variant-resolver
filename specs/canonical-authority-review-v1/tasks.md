# Canonical Authority Review v1 — Tasks

Date: 2026-09-26. Owner approval recorded: 2026-09-28. Mode: Lite / Lean Industrial. Status:
**CAR-T1–T2 complete; T3+ not started**.

After owner approval, execute sequentially. Each task is one reviewable commit. A failed owner/data
Gate stops later work without being treated as an engineering failure.

## CAR-T1 — Record source decisions **OWNER GATE** `[task_executor/doc_curator]`

- [x] Record the bounded reuse decision, access limitation, source/claim tiers, allowed fields,
  retention, publication, privacy, attribution/share-alike, reviewer role and checksum for the
  approved fixed snapshot. _(→CAR-R1,CAR-R2,CAR-R6)_

Files:

- `specs/canonical-authority-review-v1/source-approval.md`
- `data/authority-review/canonical-authority-review-v1/source-decisions.json`
- `data/authority-review/canonical-authority-review-v1/source-decisions-manifest.json`

Acceptance:

- The only approved input is the existing checked-in normalized 100-row text snapshot
  `fandom-hot-wheels-2025-pilot-r790665-v1`; no new raw page, image or media is acquired.
- `source_kind=licensed_community_snapshot` and
  `claim_tier=community_reference_snapshot_exact`; documentation states this is exact relative to
  frozen revision `790665`, not Mattel/manufacturer-certified.
- Every eligible row must bind the Wiki page, revision, `source_record_id`, normalized checksum and
  CC-BY-SA attribution/share-alike requirements.
- Current Fandom terms' unauthorized-scraping limitation is recorded; reuse approval does not claim
  that historical access was Fandom-authorized. Network/browser collection remains zero.
- Allowed mappings are `casting_name→casting`, `toy_number→identifiers`, `release_year`, `series`,
  `collector_number`, `series_position` and `variant_note`; missing `color` remains `null` and a
  `2nd Color` note cannot infer a color name.
- Reviewer role is `project_owner`, confirmation is `owner_attestation`, and resolver output is not
  exposed.
- The 1,763-row workbook stays `family_context` / `candidate_selection_only`, not exact evidence.
- The safe planning baseline records 100 rows, 38 multi-release families, 85 rows within those
  families and zero missing key identifiers, explicitly as feasibility rather than a 20/4 PASS.
- If no source supports exact review, commit the blocked result and stop.

Commit: source decisions and safe manifest only.

## CAR-T2 — Implement strict contracts `[backend]`

- [x] Add schemas/validators for source decisions, candidates, field evidence, catalog proposals,
  append-only review events and bundle manifests.
  _(→CAR-R2,CAR-R3,CAR-R4,CAR-R5,CAR-R6,CAR-R7,CAR-R8,CAR-R10)_

Files:

- `src/product_variant_resolver/canonical_authority_review.py`
- `tests/authority/test_canonical_authority_review_contract.py`
- `data/authority-review/canonical-authority-review-v1/README.md`

Acceptance:

- Tests reject unknown fields, invalid transitions, auto-promotion, stale hashes, incomplete field
  evidence, output consultation, PII, duplicates and revoked rows in approved counts.
- No network/browser/resolver/FastAPI dependency or current runtime behavior change.

Commit: contracts and contract tests only; no real authority rows.

## CAR-T3 — Approve the candidate plan **OWNER GATE** `[qa/doc_curator]`

- [ ] Propose at least four multi-release families and enough candidate releases to yield 20 valid
  variants, then obtain owner approval of the queue and review method. _(→CAR-R2,CAR-R4,CAR-R8)_

Files:

- `specs/canonical-authority-review-v1/candidate-plan.md`
- `data/authority-review/canonical-authority-review-v1/candidate-plan.json`
- `docs/evidence/canonical-authority-review-candidate-baseline.md`

Acceptance:

- Existing local context is marked `candidate_selection_only` and supplies no exact UUID/value.
- The plan groups duplicates, includes surplus candidates, and records
  `confirmation_method=owner_attestation` with reviewer role `project_owner`.
- If four plausible families cannot be nominated lawfully, record the shortfall and stop.

Commit: candidate plan and safe aggregate evidence only.

## CAR-T4 — Build the local packet and catalog proposals `[backend/qa]`

- [ ] Generate the deterministic owner packet and prepare evidence-bound proposals for candidates
  missing canonical records. _(→CAR-R2,CAR-R3,CAR-R6,CAR-R7)_

Files:

- `scripts/build_canonical_authority_review_packet.py`
- `scripts/build_canonical_catalog_record_proposals.py`
- `tests/authority/test_canonical_authority_review_packet.py`
- `data/authority-review/canonical-authority-review-v1/catalog-proposal-manifest.json`
- local-only packet/evidence under an ignored owner-configured directory

Acceptance:

- Each candidate shows all populated catalog fields, evidence refs, conflicts and owner questions;
  telemetry proves no resolver output or network access.
- Public Git receives only safe hashes/counts/metadata; repeated builds are `unchanged`.
- Proposal generation is read-only. Each catalog application requires separate owner approval and a
  separate commit, validates the parent catalog, and does not approve authority.

Commit: packet/proposal tooling and tests. Any approved catalog mutation is its own later commit.

## CAR-T5 — Review, approve and freeze the bundle **OWNER GATE** `[task_executor/qa/doc_curator]`

- [ ] Capture output-blind human reviews, bind owner attestations, apply explicit outcome
  transitions, and freeze the authority bundle. _(→CAR-R3,CAR-R4,CAR-R5,CAR-R6,CAR-R7,CAR-R8)_

Files:

- `data/authority-review/canonical-authority-review-v1/review-events.json`
- `data/authority-review/canonical-authority-review-v1/authority-candidates.json`
- `data/authority-review/canonical-authority-review-v1/approved-authority.json`
- `data/authority-review/canonical-authority-review-v1/authority-manifest.json`
- `tests/authority/test_canonical_authority_review_bundle.py`

Acceptance:

- Every approved row binds source decisions, packet/catalog/product hashes, all populated fields,
  reviewer role/time/reason, confirmation method and `resolver_output_consulted=false`.
- Conflict/insufficient/held/revoked rows remain traceable but do not count.
- At least 20 distinct variants/four families pass, or the manifest reports exact shortfalls.
- No local raw evidence/PII is committed; two `--check` runs are `unchanged`.

Commit: review event chain, frozen bundle, builder/tests and safe aggregate evidence; no RHB edit.

## CAR-T6 — Run a fresh RHB-T4 audit `[qa/doc_curator]`

- [ ] Feed the frozen CAR bundle into a versioned RHB-T4 re-audit without overwriting prior history.
  _(→CAR-R8,CAR-R9)_

Files:

- versioned RHB-T4 input adapter/tests only if required
- new versioned RHB authority artifact/manifest
- `docs/evidence/representative-hard-benchmark-authority-reaudit.md`

Acceptance:

- T4 independently rechecks permissions, hashes, field evidence, reviewer metadata, blindness,
  privacy and 20/4 composition; CAR cannot force a PASS.
- No RHB-T5 query, label or resolver run is created. RHB-T5 stays blocked unless T4 passes.

Commit: versioned re-audit and evidence only.

## CAR-T7 — Close Lean QA and documentation `[qa/doc_curator]`

- [ ] Run requirement-mapped verification and publish technical evidence, AI eval and the narrative
  Project Log. _(→CAR-R10,CAR-R11)_

Files:

- `specs/canonical-authority-review-v1/review.md`
- `docs/evidence/canonical-authority-review-v1.md`
- `docs/evidence/ai-evals/canonical-authority-review-v1.md`
- `docs/PROJECT-LOG.md`
- README/Portfolio Guide only for measured, scoped claims

Acceptance:

- QA maps CAR-R1–R11 and separates engineering PASS from the data result.
- Focused/full regression, Ruff, format, strict MyPy, compileall, deterministic/hash/link/JSON,
  secret/PII and `git diff --check` results are recorded.
- AI eval fails invented evidence, model-derived truth, privacy leaks, hidden conflicts, false second-
  reviewer claims and exaggerated benchmark-readiness claims.
- Project Log explains what changed, the problem solved, reasons/trade-offs, failures/fixes and next
  Gate rather than listing files.

Commit: QA/evidence/documentation only.

## Completion rule

- **Engineering PASS / eligible for RHB-T4 re-audit:** at least 20 valid exact variants and four
  qualifying families; RHB-T5 is still not authorized.
- **Engineering PASS / Data BLOCKED:** contracts/review evidence are sound but shortfalls remain.

There is no path that invents evidence, silently promotes a candidate, or bypasses RHB-T4.
