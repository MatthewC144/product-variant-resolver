# Human Knowledge identity-certificate set v4 — Tasks

Date: 2026-09-24. Mode: Lite / Lean Industrial. Status: **CLOSED — HICS-T1–T5/T9 complete; historical FAIL; HICS-T6–T8 blocked; Pointwise/Listwise spec next**.

Tasks execute strictly in order. HICS-T1–T4 may change the isolated v4 development source and tests,
but they must not perform retrieval or create formal v4 evidence. HICS-T5 is the historical branch
gate. If no non-reference profile passes every frozen gate, HICS-T6–T8 become blocked and execution
moves directly to the null-result branch of HICS-T9. If calibration passes, the source, certificate
inventory, profile definitions, protocol, gates, and input hashes freeze before HICS-T6 begins and
remain immutable through HICS-T9. A defect discovered after that freeze requires a new version; it
does not authorize editing v4 after seeing holdout results.

V4 is the final identity-admission attempt in the current roadmap. Whether it ends in PASS or FAIL,
HICS-T9 closes the branch and hands the project back to the separately specified No Reranker/RRF,
Neural Pointwise, and Listwise comparison. This task list does not authorize v5, private evaluation,
runtime integration, API changes, PostgreSQL changes, or variant/color recognition.

## HICS-T1 — Build and validate the public authority inventory

- [x] Load the committed 142-document Human Knowledge corpus, verify immutable upstream bindings,
  and construct the deterministic 139-key casting/family authority inventory without creating
  certificates or evaluation artifacts. _(→HICS-R1–R4, HICS-R16)_

Owner: backend responsibility under the Lite task executor.

Files:

- `src/product_variant_resolver/human_knowledge_identity_certificate_development.py`
- `tests/evaluation/test_human_knowledge_identity_certificate_development.py`

Acceptance:

- The loader reads only committed public inputs and verifies every HIC-v1, HIE-v2, and HICG-v3 hash
  fixed in `design.md` before inventory construction; mismatch fails before writes.
- Exactly 100 provisional documents map to 97 `casting:<casting_id>` authorities and 42 review-family
  documents map to 42 `review_family:<review_family_id>` authorities, for 139 keys total.
- Every source document belongs to exactly one authority; member IDs/UUIDs use deterministic lexical
  order and document grouping never claims release-level equivalence.
- Primary casting is the only certificate-claim source. Human labels and review-family aliases are
  stored only as approved future bridge surfaces; series, color, wheel, tampo, edition, packaging,
  release metadata, initial model text, and source IDs cannot enter claims.
- The inventory identifies the three duplicate-document excess records under the existing
  `83 Chevy Silverado` and `Toyota Supra` casting authorities without collapsing source documents.
- Private five-family projection paths/values and candidate rankings are absent from code paths and
  test fixtures; runtime modules do not import the v4 module.
- Focused tests cover counts, grouping, ordering, forbidden fields, hash mismatch, duplicate
  membership, and deterministic serialization. Retrieval and formal artifact counts remain zero.

## HICS-T2 — Derive minimal certificates and bounded alias bridges

- [x] Derive primary-casting claims, enumerate every minimal authority certificate, prove uniqueness
  and minimality against the complete inventory, and map approved aliases only onto existing claims.
  _(→HICS-R3–R4, HICS-R6–R8, HICS-R16)_

Owner: backend responsibility under the Lite task executor.

Files:

- `src/product_variant_resolver/human_knowledge_identity_certificate_development.py`
- `tests/evaluation/test_human_knowledge_identity_certificate_development.py`

Acceptance:

- Primary casting atomization preserves source positions and local leading-year, standalone-model,
  alphanumeric-model, and compact-model frames; digits cannot move between frames or owners.
- The current maximum remains at or below 12 claims per authority. Exceeding the frozen bound fails
  closed instead of truncating or changing the search algorithm silently.
- Ordered nonempty subsets are evaluated from smallest to largest against all 139 authority keys;
  redundant supersets are removed deterministically.
- A one-claim alphabetic certificate is allowed only when the target primary casting itself contains
  exactly one identity claim; a shared maker such as `Honda`, `BMW`, or `Bugatti` cannot certify a
  longer casting.
- Every certificate records the authority, member IDs, primary casting, ordered claims, competing
  keys, elimination steps, one-claim deletion proof, and canonical checksum.
- Complete-primary collisions are marked `unresolved_collision` and remain ineligible; no series,
  color, release, source-rank, or lexical tie-break manufactures uniqueness.
- Alias bridges retain source/target positions, relations, unmapped atoms, and checksum, and cannot
  create claims, alter digit runs, merge authorities, or turn variant metadata into identity.
- Tests independently recompute uniqueness/minimality and cover stable output, collisions, forbidden
  alias behavior, local frames, single-word authorities, and tampering. Retrieval/artifacts stay zero.

## HICS-T3 — Implement candidate-independent query support and candidate admission

- [x] Parse each query once against the complete frozen-in-memory inventory, build its authority
  support set, then apply singleton membership and all-rank primary-frame conflict preflight to
  candidates without reordering them. _(→HICS-R5–R12, HICS-R16)_

Owner: backend responsibility under the Lite task executor.

Files:

- `src/product_variant_resolver/human_knowledge_identity_certificate_development.py`
- `tests/evaluation/test_human_knowledge_identity_certificate_development.py`

Acceptance:

- Query support is built before candidates are inspected and its canonical evidence/checksum is
  byte-identical for every candidate, independent of source rank, score, UUID, or Top-5 composition.
- `reference-anchor` is comparison-only; `certificate-exact`, `certificate-structural`, and
  `certificate-bounded` implement exactly the relations and least-permissive order in `design.md`.
- Every profile requires a complete certificate, conserved query order, distinct query spans, no
  unresolved discriminative atom, and no conflicting local frame; no scalar threshold exists.
- Shared maker/generic tokens and incomplete certificates remain empty, including the declared
  `Honda Accord`, `BMW M4`, and `Bugatti Divo` adversarial patterns.
- Legitimate unique shorthand may omit non-certificate candidate words, while punctuation/spacing,
  compact segmentation, year shorthand, unique prefix, alpha edit-1, same-frame `o/0`, repeated
  digit restoration, and year uncertainty use only their frozen reason-coded bounds.
- Empty or multi-authority support sets make every candidate abstain. Singleton support admits only
  candidates mapped to that authority and only after the same rank-1-to-rank-5 primary-frame veto.
- Multiple documents under one supported authority preserve source order and disclose
  `casting_authority_only` plus `variant_not_resolved`; no release-level winner is claimed.
- Evidence validation rejects unknown relations, inconsistent checksums, overlapping query spans,
  candidate-dependent support, nonconserved digits, or invalid decision states.

## HICS-T4 — Implement historical scoring, phased CLI, and artifact lifecycle

- [x] Add immutable public-evidence loaders, exact historical scoring, conditional artifact builders,
  lifecycle validation, and the installed phase-gated CLI using only synthetic/temporary tests before
  the formal gate is run. _(→HICS-R1–R2, HICS-R13–R16)_

Owner: backend responsibility under the Lite task executor.

Files:

- `src/product_variant_resolver/human_knowledge_identity_certificate_development.py`
- `tests/evaluation/test_human_knowledge_identity_certificate_development.py`
- `pyproject.toml`

Acceptance:

- Historical calibration recomputes exactly 223 existing, 22 anchor-confidence v4, and 24 HIC-v1
  public rows with zero retrieval and reports every predeclared gate for every profile.
- The reference profile cannot survive. Eligible profiles use the frozen winner order: fewer
  negative admissions, fewer positive abstentions, fewer non-exact operations, then exact before
  structural before bounded.
- `pvr-develop-human-knowledge-identity-certificate` exposes only `--freeze-protocol`,
  `--freeze-pack`, `--collect`, `--score`, and `--check` with mutually exclusive phases.
- Historical FAIL may create only deterministic calibration JSON, manifest, and Markdown with
  `winner: null`; protocol, pack, raw, selection, private evaluation, and runtime changes stay absent.
- Historical PASS freezes source/inventory/profile/protocol/input hashes. Later phases reject source
  changes, stale hashes, denominator drift, missing/extra files, invalid order, or overwrite attempts.
- Pack validation enforces family-disjoint 16+16 balance and frozen declarations. Raw validation
  allows query, ranked candidates, work, and errors but rejects expected labels, policy decisions,
  gates, or winners at any depth.
- Repeated phases return byte-identical `unchanged`; collection never retries error rows; scoring
  reads only frozen raw bytes and joins labels afterward.
- Tests use temporary/synthetic inputs and do not execute the real 223/22/24 gate, author the real
  holdout, inspect private evidence, or perform retrieval.

## HICS-T5 — Run pre-freeze QA and the historical branch gate

- [x] Verify the implementation, execute the public 223/22/24 zero-retrieval calibration exactly
  once, and freeze the protocol only if a non-reference profile passes every exact gate.
  _(→HICS-R1–R2, HICS-R5–R14, HICS-R16)_

Owner: QA responsibility under the Lite task executor.

Files always created on a completed gate:

- `reports/human-knowledge-identity-certificate-development-v4/historical-calibration.json`
- `reports/human-knowledge-identity-certificate-development-v4/historical-calibration-manifest.json`
- `reports/human-knowledge-identity-certificate-development-v4/historical-calibration.md`

Files created only on PASS:

- `data/evaluation/human-knowledge-identity-certificate-development-v4/protocol/protocol.json`
- `data/evaluation/human-knowledge-identity-certificate-development-v4/protocol/protocol-manifest.json`
- `data/evaluation/human-knowledge-identity-certificate-development-v4/inventory/inventory.json`
- `data/evaluation/human-knowledge-identity-certificate-development-v4/inventory/inventory-manifest.json`

Acceptance:

- Targeted Ruff format/check, target-local strict MyPy, compile, focused tests, and related identity
  regressions pass before the branch command; upstream hashes and absence/presence invariants match.
- Calibration denominators are exactly 223/22/24 and retrieval calls are exactly zero.
- PASS branch has at least one non-reference profile passing every HICS-R13 gate; protocol/inventory
  bind all frozen rules, inputs, checksums, gate definitions, and winner order; repeated freeze is
  byte-identical `unchanged`.
- FAIL branch stores `winner: null` with every failed gate, creates no protocol/inventory/pack/raw/
  selection artifact, marks HICS-T6–T8 blocked, and never edits a profile after results are visible.
- The measured result, source hash, artifact hashes, invocation, and branch decision are added to
  tests/documentation only after the evidence exists; no result is described in advance.

## HICS-T6 — Author post-freeze negatives and freeze the 16+16 holdout

**Blocked:** HICS-T5 returned historical FAIL on 2026-09-24; this conditional task will not execute.

- [ ] Author the separate frozen negative declarations and materialize the family-disjoint public
  holdout without retrieval or source/profile changes. _(→HICS-R15–R16)_

Owner: public evaluation-data responsibility under the Lite task executor.

Files created:

- `specs/human-knowledge-identity-certificate-development/holdout-negative-declarations.json`
- `data/evaluation/human-knowledge-identity-certificate-development-v4/pack/development-pack.json`
- `data/evaluation/human-knowledge-identity-certificate-development-v4/pack/development-pack-manifest.json`

Acceptance:

- Exactly 16 positive cases use 16 distinct public authorities/documents unused by prior positive
  packs, four each for unique partial, punctuation/compact, bounded edit/abbreviation, and
  year/numeric certificate challenges.
- Exactly 16 negative declarations contain four shared-maker incomplete, four same-maker model
  substitutions, four numeric/alphanumeric conflicts, and four ambiguous/context-overlap cases.
- Negative normalized queries/identities are corpus-absent and do not repeat prior negative packs;
  positive/negative families are disjoint according to the frozen contract.
- Every positive has a frozen certificate proof; every negative states the expected empty/ambiguous/
  conflict reason without using private labels or retrieval results.
- Pack manifest binds frozen source, inventory, protocol, declarations, ordering, and exact counts;
  repeated freeze is byte-identical `unchanged` and retrieval remains zero.

## HICS-T7 — Collect and preserve 32 label-blind Top-5 rows once

**Blocked:** HICS-T5 returned historical FAIL, so HICS-T6 did not execute and this task cannot begin.

- [ ] Retrieve each frozen holdout query exactly once and persist raw evidence before expected labels
  or profile decisions are joined. _(→HICS-R15–R16)_

Owner: backend execution with QA evidence checks.

Files created:

- `data/evaluation/human-knowledge-identity-certificate-development-v4/raw/raw.json`
- `data/evaluation/human-knowledge-identity-certificate-development-v4/raw/raw-manifest.json`

Acceptance:

- Exactly 32 Top-5 calls produce 32 ordered rows; every candidate maps to the committed public corpus
  and retains source rank, score, retrieval work, and error fields.
- Raw bytes contain no expected labels, case classes, profile decisions, eligibility gates, winner,
  or private evaluation values.
- Errors are preserved without retry, removal, replacement, or query edits.
- Source, inventory, protocol, declarations, and pack hashes still match before and after collection.
- Repeating `--collect` returns `unchanged`, makes zero additional calls, and preserves exact bytes.

## HICS-T8 — Score frozen evidence and lock the public verdict

**Blocked:** HICS-T5 returned historical FAIL, so HICS-T6–T7 did not execute and this task cannot begin.

- [ ] Join frozen labels only after raw persistence, score every historical survivor, write selection
  evidence once, and add measured-artifact regressions without changing frozen v4 code or inputs.
  _(→HICS-R13–R16)_

Owner: QA responsibility under the Lite task executor.

Files created or updated:

- `reports/human-knowledge-identity-certificate-development-v4/selection.json`
- `reports/human-knowledge-identity-certificate-development-v4/selection.md`
- `tests/evaluation/test_human_knowledge_identity_certificate_development.py`

Acceptance:

- Every surviving profile reports all historical gates, 16/16 positive hits, 0/16 negative nonempty
  results, computation errors, admitted/abstained counts, equivalence uses, and deterministic status.
- Only a profile passing every historical and holdout gate can win under the already-frozen order.
- `winner: null` authorizes no private evaluation or runtime work. A public winner authorizes only a
  separately specified private shadow evaluation; it still does not alter runtime.
- Selection binds source/inventory/protocol/pack/raw bytes; rerun is `unchanged`, and `--check`
  independently recomputes results and rejects tampering.
- Tests lock measured counts and winner/null behavior without changing certificate/profile code.

## HICS-T9 — Complete branch-aware Lite QA, documentation, GitHub delivery, and handoff

- [x] Close either the historical-FAIL branch or the completed-holdout branch with honest QA,
  requirements coverage, evidence, AI-eval, narrative documentation, and a Product-Variant-Resolver-
  only GitHub commit; then hand the roadmap to Pointwise/Listwise specification.
  _(→HICS-R1–R16)_

Owner: QA and documentation responsibilities under the Lite task executor.

Files created or updated:

- `specs/human-knowledge-identity-certificate-development/review.md`
- `docs/evidence/human-knowledge-identity-certificate-development-v4.md`
- `docs/evidence/ai-evals/human-knowledge-identity-certificate-v4.md`
- `docs/decisions/product-variant-resolver.md`
- `docs/PROJECT-LOG.md`
- `docs/REAL-CATALOG-ROADMAP.md`
- `README.md`

Acceptance:

- Focused/related/full tests, targeted Ruff format/check, target-local strict MyPy, compile, installed
  CLI, repeated integrity checks, and staged `git diff --check` pass; known repository-wide debt is
  reported without unrelated formatting or refactoring.
- `review.md` maps HICS-R1–R16 to tests/artifacts and separates implementation integrity, historical
  eligibility, holdout eligibility, private eligibility, and runtime authorization.
- FAIL branch documents `winner: null`, zero new retrieval, blocked conditional tasks, and absent
  downstream effects without pretending the experiment reached holdout.
- PASS/holdout branch documents exactly-once collection, frozen selection, and whether the result is
  eligible only for a separately specified private shadow evaluation.
- AI-eval covers grounding, public/private separation, leakage, integrity, certificate minimality,
  candidate independence, explainability, positive preservation, negative safety, and release safety.
- Project Log narrates what changed, the problem solved, code areas, selection rationale,
  alternatives, measurements, failure modes, and next gate—not only a checklist.
- No API, Dual RAG, PostgreSQL, canonical identity, release, color, wheel, tampo, edition, or packaging
  behavior changes. V4 does not automatically create or authorize v5.
- Roadmap explicitly moves next to a new Lite spec comparing No Reranker/RRF, Neural Pointwise, and
  Listwise on one frozen candidate pool; this task does not implement that comparison.
- Commit and push contain only `Product Variant Resolver` files. Parent `AGENTS.md`, `.codex`, and
  unrelated workspace files remain excluded, and GitHub `main` equals local `HEAD` after delivery.

## Execution checkpoint

The owner confirmed HICS-R1–R16, the v4 design, and this task list in sequence before implementation.
HICS-T1–T5 are complete. The isolated v4 source builds a deterministic in-memory inventory of 142
public documents grouped into 139 authority keys, derives 460 primary-casting-only claims, proves
401 admissibly minimal certificates, and records 101 alias bridges without adding claims. Seven
shorter/contained primary identities remain explicit `unresolved_collision`; the other 132
authorities each have at least one certificate. Query support now parses once against the complete
inventory for exact, structural, or bounded profiles, fails closed on residual/ambiguous/numeric
conflict evidence, and reuses one checksum for all rank-ordered candidate membership decisions.
Multiple documents under one casting authority remain explicitly variant-unresolved. Immutable public loaders,
exact 223/22/24 offline scoring, conditional protocol/inventory/pack/raw/selection builders, lifecycle
validation, and the five-phase installed CLI passed pre-freeze QA. The one-time formal calibration
returned `historical_calibration_fail`: exact/structural/bounded preserved 42/82/137 of 168 existing
positive hits and all reached zero absent-identity output, but none passed every frozen positive gate.
The report records `winner: null`, exact 223/22/24 denominators, zero retrieval and zero computation
errors. Only the three calibration files exist; protocol, inventory, pack, raw, selection and private
evaluation artifacts remain absent. HICS-T6–T8 are blocked. After adding measured regressions the
focused/related/full counts are 60/181/924. HICS-T9 closes the branch with QA review, evidence,
AI-eval, README/decision/log updates, and Product-Variant-Resolver-only GitHub delivery. The next
work item is a new Lite Pointwise/Listwise comparison spec; v5 and runtime integration stay absent.
