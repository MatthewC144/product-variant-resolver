# Human Knowledge identity-claim graph v3 — Tasks

Date: 2026-09-22. Mode: Lite / Lean Industrial. Status: **historical-FAIL branch closed; HICG-T1–T4/T8 complete; HICG-T5–T7 blocked**.

Tasks execute strictly in order. HICG-T1–T3 may change the V3 development source. HICG-T4 is the
branching historical gate: if no non-reference policy passes every exact gate, HICG-T5–T7 become
blocked and execution moves directly to the null-result branch of HICG-T8. If calibration passes,
the source/protocol freeze makes the development source immutable through HICG-T8; a later source
defect requires a new version.

## HICG-T1 — Implement the public grammar and immutable query graph

- [x] Build full-query atomization, public identity grammar, context classification, compact
  segmentation, bounded equivalence relations, local frames, graph serialization, and checksum
  reuse without evaluating policies or creating artifacts. _(→HICG-R1–R7, HICG-R10, HICG-R15)_

Owner: backend responsibility under the Lite task executor.

Files:

- `src/product_variant_resolver/human_knowledge_identity_claim_graph_development.py`
- `tests/evaluation/test_human_knowledge_identity_claim_graph_development.py`

Acceptance:

- Grammar reads only committed casting and approved-alias identity text and verifies public input
  uniqueness; forbidden metadata and private paths are absent from graph construction.
- One query produces one canonical graph/checksum reused byte-for-byte for every candidate.
- Full-query offsets and source tokens survive normalization; apostrophe years remain numeric.
- Context vocabulary and identity precedence preserve `Tesla Model S Plaid` while separating public
  wrappers such as `listing`, `sale`, `warehouse`, and `unboxed`.
- Compact segmentation conserves every digit and covers `2020ram1500rebel` plus compact context with
  identity; ambiguous segmentations resolve only through the frozen lexicographic order.
- Unique prefix and alphabetic edit-1 relations cover the declared examples and reject ambiguous,
  numeric, unsupported, or non-unique transformations.
- Leading-year, standalone-model, alphanumeric-model, and compact-model frames have stable local
  owners, ordered edges, roles, reason codes, and deterministic canonical JSON.
- No protocol, pack, raw, calibration, or selection artifact is created and retrieval calls are zero.

## HICG-T2 — Implement candidate evidence, all-rank conflict preflight, and policies

- [x] Compare primary casting/approved aliases against the immutable graph, enforce the universal
  hard-conflict veto, and implement the reference plus four frozen structural policies without
  changing source candidate order. _(→HICG-R5–R10, HICG-R15–R16)_

Owner: backend responsibility under the Lite task executor.

Files:

- `src/product_variant_resolver/human_knowledge_identity_claim_graph_development.py`
- `tests/evaluation/test_human_knowledge_identity_claim_graph_development.py`

Acceptance:

- Frame comparison implements only exact, year suffix, `o/0`, repeated-digit restoration, and
  leading-year uncertainty-`x` rules; unequal digit substitution never becomes equivalent.
- Primary-casting numeric conflict cannot be hidden by selecting an alias without that frame.
- Hard-conflict preflight runs before source-rank and coverage branches for ranks 1–5.
- Rank-1 and secondary `R32`/`R33` versus `BNR34` cases abstain with explicit frame/reason evidence.
- `reference-anchor`, `claim-conflict-veto`, `claim-bilateral`,
  `claim-query-conservation`, and `claim-decision-list` exactly match design order.
- Secondary candidates can reach coverage `>= 0.75` only after their configuration's structural
  rules pass; source ranks and ordering remain unchanged.
- Candidate evidence contains every HICG-R15 field and rejects unknown states, inconsistent graph
  checksums, nonfinite values, or candidate-dependent graph changes.
- Focused regressions cover every positive and adversarial example declared in `design.md`.

## HICG-T3 — Implement historical calibration, phased CLI, and artifact validators

- [x] Add immutable public-evidence loaders, exact historical scoring, conditional artifact builders,
  lifecycle validation, and the installed phase-gated CLI before any source freeze or retrieval.
  _(→HICG-R1–R2, HICG-R11–R16)_

Owner: backend responsibility under the Lite task executor.

Files:

- `src/product_variant_resolver/human_knowledge_identity_claim_graph_development.py`
- `tests/evaluation/test_human_knowledge_identity_claim_graph_development.py`
- `pyproject.toml`

Acceptance:

- Historical calibration recomputes exactly 223 existing, 22 v4, and 24 HIC-v1 public rows without
  retrieval and reports every HICG-R11 gate for every policy.
- The five frozen upstream hashes in `design.md` plus all corpus/evidence inputs are verified before
  graph construction; mismatch fails without writes.
- `--freeze-protocol` writes a protocol only when a non-reference policy passes all gates; otherwise
  it may write only the deterministic null-calibration JSON, manifest, and Markdown report.
- Pack builder enforces the post-freeze declaration path/schema, 16+16 balance, document/family
  non-reuse, corpus-absent negatives, deterministic selection, and zero retrieval.
- Collector permits exactly one ordered Top-5 row per frozen query; repeated collection is
  `unchanged` with zero new calls and preserved errors.
- Raw schema permits query, ranked candidates, retrieval work, and errors but forbids expected labels,
  policy decisions, gates, or winner fields.
- Scorer uses frozen raw bytes, reports all historical/new gates, and applies the exact winner order.
- CLI exposes only `--freeze-protocol`, `--freeze-pack`, `--collect`, `--score`, and `--check`; invalid
  phase order, stale hashes, denominator drift, mutation, or overwrite attempts fail closed.

## HICG-T4 — Run pre-freeze QA and the historical branch gate

- [x] Verify the implementation, execute public historical calibration, and freeze source/protocol
  only if at least one non-reference policy passes every exact historical gate.
  _(→HICG-R1–R2, HICG-R8–R12, HICG-R15–R16)_

Owner: QA responsibility under the Lite task executor.

Files always created on a completed gate:

- `reports/human-knowledge-identity-claim-graph-development-v3/historical-calibration.json`
- `reports/human-knowledge-identity-claim-graph-development-v3/historical-calibration-manifest.json`
- `reports/human-knowledge-identity-claim-graph-development-v3/historical-calibration.md`

Files created only on PASS:

- `data/evaluation/human-knowledge-identity-claim-graph-development-v3/protocol/protocol.json`
- `data/evaluation/human-knowledge-identity-claim-graph-development-v3/protocol/protocol-manifest.json`

Acceptance:

- Targeted Ruff format/check, MyPy, compile, focused tests, and all related historical regressions
  pass before the branch command runs.
- Calibration denominators are exactly 223/22/24, all upstream hashes match, and retrieval calls are
  exactly zero.
- PASS branch: at least one non-reference policy passes every HICG-R11 gate; protocol binds source,
  grammar/context/equivalence rules, policies, gates, winner order, declaration schema/path, and
  upstream hashes; repeated freeze is byte-identical `unchanged`.
- FAIL branch: calibration stores `winner: null` plus every failed gate, creates no protocol/pack/raw/
  selection artifact, marks HICG-T5–T7 blocked, and does not alter a policy after results are visible.
- On PASS, record the development source hash and prohibit source changes through HICG-T8.

## HICG-T5 — Author post-freeze negatives and freeze the 16+16 holdout

**Conditional:** execute only after HICG-T4 PASS.

**Status:** blocked by the HICG-T4 historical FAIL; no protocol was authorized.

- [ ] Author the separate frozen negative declarations and materialize the family-disjoint public
  holdout without retrieval or source changes. _(→HICG-R13, HICG-R15–R16)_

Owner: public evaluation-data responsibility under the Lite task executor.

Files created:

- `specs/human-knowledge-identity-claim-graph-development/holdout-negative-declarations.json`
- `data/evaluation/human-knowledge-identity-claim-graph-development-v3/pack/development-pack.json`
- `data/evaluation/human-knowledge-identity-claim-graph-development-v3/pack/development-pack-manifest.json`

Acceptance:

- Exactly 16 positives use 16 distinct public documents unused by v4/HIC-v1 positive packs, four
  each for leading-year/context, OCR/numeric, edit/abbreviation, and compact challenges.
- Exactly 16 negatives contain four cases each for numeric model conflict, same-maker model
  substitution, compact-digit conflict, and context overlap.
- Every negative normalized identity/query is corpus-absent and does not repeat v4/HIC-v1 negatives.
- Manifest binds the already-frozen source/protocol and exact declarations hash, records zero
  retrieval, and validates the complete balance/non-reuse contract.
- Repeated pack freeze returns byte-identical `unchanged`; frozen source bytes do not change.

## HICG-T6 — Collect and preserve 32 label-blind Top-5 rows once

**Conditional:** execute only after HICG-T5 PASS.

**Status:** blocked because HICG-T5 cannot execute after the historical FAIL.

- [ ] Retrieve every frozen holdout query exactly once and persist raw evidence before reading labels
  for scoring. _(→HICG-R14–R16)_

Owner: backend execution with QA evidence checks.

Files created:

- `data/evaluation/human-knowledge-identity-claim-graph-development-v3/raw/raw.json`
- `data/evaluation/human-knowledge-identity-claim-graph-development-v3/raw/raw-manifest.json`

Acceptance:

- Exactly 32 retrieval calls produce 32 rows in frozen pack order with candidate limit five.
- Every candidate maps to the public corpus and preserves source rank, score, work, and error fields.
- Raw bytes contain no expected labels, policy decisions, gates, or winner information.
- Errors remain stored and are never retried or removed.
- Repeating `--collect` returns `unchanged`, makes zero new retrieval calls, and preserves exact bytes.
- Frozen source, protocol, pack, and declaration hashes still match.

## HICG-T7 — Score frozen evidence and lock the public verdict

**Conditional:** execute only after HICG-T6 completes.

**Status:** blocked because no pack or label-blind raw evidence is authorized.

- [ ] Join frozen labels only after raw persistence, score every surviving policy, write selection
  evidence once, and add measured-artifact regression tests without changing frozen source.
  _(→HICG-R11, HICG-R14–R16)_

Owner: QA responsibility under the Lite task executor.

Files created or updated:

- `reports/human-knowledge-identity-claim-graph-development-v3/selection.json`
- `reports/human-knowledge-identity-claim-graph-development-v3/selection.md`
- `tests/evaluation/test_human_knowledge_identity_claim_graph_development.py`

Acceptance:

- Every configuration reports all historical gates, 16/16 positive and 0/16 negative gates, exact
  errors, admitted/abstained counts, equivalence counts, and deterministic eligibility.
- Only a policy passing every historical and holdout gate can win under the frozen ordering.
- If no policy is eligible, persist `winner: null`; that result authorizes no private evaluation or
  runtime change.
- Selection and manifests bind source/protocol/pack/raw bytes; rerun returns `unchanged`.
- `--check` independently recomputes graph/evidence/results and rejects any tampering.
- Tests lock measured counts and winner/null behavior without changing policy code.

## HICG-T8 — Complete branch-aware Lite QA, documentation, and GitHub delivery

- [x] Close either the historical-FAIL branch or the completed-holdout branch with honest QA,
  requirements coverage, evidence, AI-eval, decision/log updates, and a Product-Variant-Resolver-only
  GitHub commit. _(→HICG-R1–R16)_

Owner: QA and documentation responsibilities under the Lite task executor.

Files created or updated:

- `specs/human-knowledge-identity-claim-graph-development/review.md`
- `docs/evidence/human-knowledge-identity-claim-graph-development-v3.md`
- `docs/evidence/ai-evals/human-knowledge-identity-claim-graph-v3.md`
- `docs/decisions/product-variant-resolver.md`
- `docs/PROJECT-LOG.md`
- `docs/REAL-CATALOG-ROADMAP.md`
- `README.md`

Acceptance:

- Focused/related/full tests, targeted Ruff format/check, targeted MyPy, compile, installed CLI,
  repeated integrity checks, and staged `git diff --check` pass; any known repo-wide debt is reported
  rather than silently reformatted into this experiment.
- `review.md` maps HICG-R1–R16 to tests/artifacts and separates implementation integrity, historical
  eligibility, holdout eligibility, and runtime authorization.
- FAIL branch documents the null calibration, zero new retrieval, blocked T5–T7, and absent downstream
  effects without pretending the experiment reached holdout.
- PASS/holdout branch documents exactly-once collection, frozen selection result, and whether the
  winner is eligible for a separately specified private shadow evaluation only.
- AI-eval covers grounding, public/private separation, leakage, integrity, explainability, positive
  preservation, negative safety, and release-boundary compliance.
- Project Log narrates what changed, the problem solved, code areas, method choices, alternatives,
  measurements, failure mode, and next gate—not only a checklist.
- No API/Dual RAG/PostgreSQL/canonical/release/color behavior changes.
- Commit and push include only `Product Variant Resolver` files; workspace `AGENTS.md`, `.codex`, and
  unrelated parent files remain excluded, and GitHub `main` equals local `HEAD` after delivery.

## Execution checkpoint

The owner confirmed this task list with `繼續幫我下一步` before implementation. HICG-T1–T4 and the
historical-FAIL closure branch of HICG-T8 are complete. Pre-freeze QA passed, then the formal
zero-retrieval 223/22/24 calibration returned `historical_calibration_fail`, `winner: null`, and no
survivors. Repeating `--freeze-protocol` returned `calibration_failed_unchanged`; repeated `--check`
returned `valid`. Only the three required calibration files exist. HICG-T5–T7 remain blocked.
Review, evidence, AI-eval, README, decision, roadmap, and Project Log now publish the null result;
51 focused, 196 related, and 864 full repository tests pass without modifying the frozen source.
