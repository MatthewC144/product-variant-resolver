# Human Knowledge query-global identity envelope — Tasks

Date: 2026-09-21. Mode: Lite / Lean Industrial. Status: **HIE-T3 complete with FAIL; HIE-T4–T7 blocked**.

Tasks execute strictly in order. HIE-T1–T2 may change implementation. HIE-T3 is a branching gate:
if no non-reference policy passes every historical calibration gate, the experiment stops without a
protocol, pack, or retrieval. If calibration passes and the protocol is frozen, HIE-T4–T7 must not
modify the development source; a later product-code defect requires a new version.

## HIE-T1 — Implement the query-global envelope primitives

- [x] Build the public anchor index, one-envelope-per-query representation, numeric-frame
  conservation, and structural shorthand equivalence without creating artifacts or running
  retrieval. _(→HIE-R1–R7, HIE-R10)_

Owner: backend responsibility under the Lite task executor.

Files:

- `src/product_variant_resolver/human_knowledge_identity_envelope_development.py`
- `tests/evaluation/test_human_knowledge_identity_envelope_development.py`

Acceptance:

- Anchor index uses only casting/approved aliases from the committed 142-document corpus.
- One query produces one envelope/checksum reused byte-for-byte for every candidate.
- Offsets, leading numeric inclusion, unknown model atoms, multiple anchors, and unanchored state
  have focused tests.
- `88`/`1988` passes only the general `year_suffix_equivalent` rule; `R33`/`R34`, `R33`/`BNR34`, and
  `M2`/`M4` remain conflicts.
- Compact/fuzzy alignment cannot consume or omit unequal digit runs.
- Source contains no private path; no protocol, pack, raw, or report directory exists.

## HIE-T2 — Implement policies, historical calibration, phased CLI, and validators

- [x] Complete the five-policy engine, historical rescoring, post-freeze pack builder, exactly-once
  collection, scoring, integrity validators, and installed CLI before freezing source.
  _(→HIE-R8–R14)_

Owner: backend responsibility under the Lite task executor.

Files:

- `src/product_variant_resolver/human_knowledge_identity_envelope_development.py`
- `tests/evaluation/test_human_knowledge_identity_envelope_development.py`
- `pyproject.toml`

Acceptance:

- All categorical states and five ordered policies match `design.md`; ranks 2–5 retain coverage
  `>= 0.75` and source order.
- Historical calibration recomputes existing 223, v4 22, and HIC-v1 24 rows without retrieval and
  reports every exact gate per policy.
- Protocol freeze refuses to proceed unless at least one non-reference policy passes every
  historical gate.
- Pack builder uses the frozen selection rules and the fixed post-freeze declaration schema/path.
- CLI exposes only `--freeze-protocol`, `--freeze-pack`, `--collect`, `--score`, and `--check` and
  rejects invalid phase order.
- Raw schema cannot contain expected labels or admission decisions; validators reject stale hashes,
  denominator drift, envelope disagreement, omitted digits, invalid states/reasons, or nonfinite
  values.

## HIE-T3 — Run the historical calibration gate and freeze protocol if eligible

- [x] Pass pre-freeze QA, run the public historical calibration, and freeze source/protocol only if
  at least one non-reference policy is fully eligible. _(→HIE-R1–R2, HIE-R8–R13)_

Owner: QA responsibility under the Lite task executor.

Files created only on PASS:

- `data/evaluation/human-knowledge-identity-envelope-development-v2/protocol/*`

Acceptance:

- Targeted Ruff/format, MyPy, compile, focused tests, and related regression tests pass before
  freezing.
- Calibration reports exact historical denominators and performs zero retrieval calls.
- PASS branch: protocol binds source, corpus/upstream hashes, envelope rules, policies, declaration
  schema/path, gates, and winner order; repeated freeze is byte-identical `unchanged`.
- FAIL branch: preserve a public calibration report with no protocol/pack/raw, mark T4–T7 blocked,
  and do not invent or alter a policy after reading failures.
- On PASS, the development source hash becomes immutable through T7.

## HIE-T4 — Author post-freeze negatives and freeze the 16+16 holdout pack

**BLOCKED:** HIE-T3 produced zero eligible non-reference policies, so no protocol exists.

- [ ] After a successful protocol freeze, author the separate negative declarations file and freeze
  the family-disjoint 32-case pack without retrieval. _(→HIE-R3, HIE-R9, HIE-R13)_

Owner: public evaluation-data responsibility under the Lite task executor.

Files created:

- `specs/human-knowledge-identity-envelope-development/holdout-negative-declarations.json`
- `data/evaluation/human-knowledge-identity-envelope-development-v2/pack/*`

Acceptance:

- Exactly 16 positives come from 16 documents unused by v4/HIC-v1 positives, four per positive
  challenge style.
- Exactly 16 new absent identities appear, four per declared negative category; identity/query
  normalization repeats no v4/HIC-v1 negative and matches no corpus casting/alias.
- Pack manifest binds the already-frozen protocol and exact declarations hash and records zero
  retrieval.
- Repeating pack freeze returns byte-identical `unchanged`; the source hash remains frozen.

## HIE-T5 — Collect and preserve 32 label-blind raw rows exactly once

**BLOCKED:** HIE-T4 cannot create a pack after the HIE-T3 calibration failure.

- [ ] Execute one Top-5 retrieval per frozen holdout query and persist raw evidence before scoring.
  _(→HIE-R9, HIE-R13)_

Owner: backend execution with QA evidence checks.

Files created:

- `data/evaluation/human-knowledge-identity-envelope-development-v2/raw/raw.json`
- `data/evaluation/human-knowledge-identity-envelope-development-v2/raw/raw-manifest.json`

Acceptance:

- Exactly 32 retrieval calls and 32 ordered rows are recorded.
- Raw contains query, candidate, rank, retrieval work, and errors but no expected label or policy
  decision.
- Every candidate maps to a public corpus UUID and all ranks/scores validate.
- Repeating collection returns `unchanged`, executes zero new retrieval calls, and preserves errors.

## HIE-T6 — Score the frozen policies and lock the public verdict

**BLOCKED:** No protocol, pack, or new raw rows are authorized by HIE-T3.

- [ ] Score historical and new evidence from frozen bytes, emit selection artifacts once, and add
  real-artifact regression tests without changing source. _(→HIE-R10–R14)_

Owner: QA responsibility under the Lite task executor.

Files created or updated:

- `reports/human-knowledge-identity-envelope-development-v2/selection.json`
- `reports/human-knowledge-identity-envelope-development-v2/selection.md`
- `tests/evaluation/test_human_knowledge_identity_envelope_development.py`

Acceptance:

- Every policy reports all existing, v4, HIC-v1, new-positive, new-negative, and error gates.
- Only a policy passing every exact gate can win under the frozen ordering.
- No eligible policy produces a persisted null winner and authorizes no private/runtime step.
- `--check` independently recomputes evidence and rejects pack/protocol/raw/result tampering.
- Artifact tests lock measured counts and deterministic winner/null behavior.

## HIE-T7 — Complete Lite QA, documentation, and GitHub delivery

**BLOCKED within this experiment:** HIE-T3 stopped the conditional HIE-T4–T7 branch. Repository-level
failure documentation may still be committed through a separate closure/delivery step, but no HIE
holdout, scoring, private evaluation, or runtime claim may be created.

- [ ] Verify the repository, write review/evidence/AI-eval/decision/log updates, test the installed
  CLI, then commit and push only Product Variant Resolver files. _(→HIE-R1–R14)_

Owner: QA and documentation responsibilities under the Lite task executor.

Files created or updated:

- `specs/human-knowledge-identity-envelope-development/review.md`
- `docs/evidence/human-knowledge-identity-envelope-development-v2.md`
- `docs/evidence/ai-evals/human-knowledge-identity-envelope-v2.md`
- `docs/decisions/product-variant-resolver.md`
- `docs/PROJECT-LOG.md`
- `docs/REAL-CATALOG-ROADMAP.md`
- `README.md`

Acceptance:

- Focused/related/full tests, Ruff/format, MyPy, compile, installed CLI, repeated integrity checks,
  and staged `git diff --check` pass.
- Review maps HIE-R1–R14 to evidence and separates implementation integrity, calibration eligibility,
  holdout eligibility, and runtime authorization.
- Project Log explains the problem, code area, choices, measured result, failure mode, and next gate
  in narrative form.
- No API/Dual RAG/PostgreSQL/canonical/release/color behavior changes.
- Commit excludes workspace agent/config files; GitHub `main` equals local `HEAD`.

## Execution checkpoint

The owner confirmed this task list before implementation. HIE-T1–T3 are complete. HIE-T3 produced a
deterministic FAIL with zero eligible non-reference policies, so the conditional HIE-T4–T7 branch is
blocked. A later technical attempt requires a new versioned specification; it may not modify this
experiment's source or calibration evidence.

## Repository closure outside the conditional HIE-T7 branch

- [x] Archive the FAIL with QA review, evidence, AI-eval, README, decisions, and Project Log; run
  full repository tests and prepare a Product-Variant-Resolver-only Git commit without creating any
  HIE-T4–T6 artifact. This closure publishes the stopped experiment and does not mark HIE-T7's
  successful-holdout branch complete.
