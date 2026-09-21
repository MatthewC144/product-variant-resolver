# Human Knowledge candidate-specific identity contradiction — Tasks

Date: 2026-09-21. Mode: Lite / Lean Industrial. Status: **HIC-T1–T6 complete**.

Tasks execute strictly in order. Tasks 1–2 may change implementation. After Task 3 freezes source
hashes, Tasks 4–6 must not modify the development module. If a product-code defect is discovered
after freezing, preserve all artifacts, stop the run, and start a new version instead of overwriting
v1 evidence.

## HIC-T1 — Build the unfrozen public pack constructor

- [x] Implement deterministic selection of 12 positive-preservation cases and declarations for 12
  new absent-identity contradiction cases. _(→HIC-R1–R3, HIC-R5)_

Owner: backend responsibility under the Lite task executor.

Files:

- `src/product_variant_resolver/human_knowledge_identity_contradiction_development.py`
- `tests/evaluation/test_human_knowledge_identity_contradiction_development.py`

Acceptance:

- Builder produces exactly 12 positives and 12 negatives with unique IDs.
- Positives exclude all ten v4 positive source IDs, cover at least ten knowledge documents, have a
  correct committed rank-1 result, and cover all four positive challenge styles.
- Negatives are absent from every normalized casting/alias, repeat no v4 negative identity/query,
  and contain exactly three cases in each of the four declared contradiction types.
- Source contains no private local artifact path and performs no retrieval during construction.
- Focused builder/privacy tests pass; no pack file is frozen yet.

## HIC-T2 — Implement the complete alignment, collection, scoring, and integrity engine

- [x] Implement atomization, identity-span selection, ordered alignment, IDF residuals, numeric
  conflicts, the seven-policy grid, phased CLI, scoring, and validators before freezing any source
  hash. _(→HIC-R4–R11)_

Owner: backend responsibility under the Lite task executor.

Files:

- `src/product_variant_resolver/human_knowledge_identity_contradiction_development.py`
- `tests/evaluation/test_human_knowledge_identity_contradiction_development.py`
- `pyproject.toml`

Acceptance:

- Alignment emits every required evidence field with valid offsets and no reused/crossed atoms.
- Exact, prefix, fuzzy, compact, OCR substitution, same-frame numeric conflict, residual weighting,
  deterministic tie-breaking, rank-1 policies, and rank-2–5 coverage behavior have focused tests.
- CLI exposes only the five declared phases and rejects invalid phase ordering.
- Raw schema cannot contain `expected`, labels, or case-level decisions.
- Scoring recomputes the 223-row regression, v4 22-row gates, and new 24-row gates without retrieval.
- Validators reject tampering, nonfinite values, unknown reason codes, stale hashes, or denominator
  drift; source is ready to become immutable.

## HIC-T3 — Pass the pre-freeze gate and freeze pack plus protocol

- [x] Run pre-freeze static/focused QA, then create the immutable pack and protocol in that order.
  _(→HIC-R1–R6, HIC-R10)_

Owner: QA responsibility under the Lite task executor.

Files created:

- `data/evaluation/human-knowledge-identity-contradiction-development-v1/pack/*`
- `data/evaluation/human-knowledge-identity-contradiction-development-v1/protocol/*`

Acceptance:

- Targeted Ruff/format, MyPy, compile, and focused tests pass before freezing.
- Pack is created first and records `retrieval_executed: false`.
- Protocol binds exact pack, source, corpus, upstream-public-artifact hashes, seven policies, rules,
  gates, and winner order; it also records `retrieval_executed: false`.
- Repeating both freeze commands returns `unchanged` with byte-identical artifacts.
- From this point through Task 6, the development source file is not modified.

## HIC-T4 — Collect and preserve the label-blind raw rows exactly once

- [x] Execute one Top-5 retrieval for each frozen new query and persist raw evidence before scoring.
  _(→HIC-R7, HIC-R10)_

Owner: backend execution with QA evidence checks.

Files created:

- `data/evaluation/human-knowledge-identity-contradiction-development-v1/raw/raw.json`
- `data/evaluation/human-knowledge-identity-contradiction-development-v1/raw/raw-manifest.json`

Acceptance:

- Exactly 24 retrieval calls and 24 ordered rows are recorded.
- Raw data contains query, candidate, rank, retrieval work, and error fields but no expected labels.
- Each candidate maps to a public corpus UUID and all scores/fields validate.
- Repeating collection returns `unchanged` and performs zero new retrieval calls.
- Any retrieval error remains recorded and is not retried or removed.

## HIC-T5 — Score the frozen policies and lock the product verdict

- [x] Score all seven policies from frozen raw bytes, emit the selection artifacts once, and add
  real-artifact tests without changing the frozen development source. _(→HIC-R4–R10)_

Owner: QA responsibility under the Lite task executor.

Files created or updated:

- `reports/human-knowledge-identity-contradiction-development-v1/selection.json`
- `reports/human-knowledge-identity-contradiction-development-v1/selection.md`
- `tests/evaluation/test_human_knowledge_identity_contradiction_development.py`

Acceptance:

- Every configuration reports all old, v4, new-positive, new-negative, and error gates.
- Winner follows the frozen ordering only when every exact HIC-R8 gate passes.
- If no policy qualifies, `winner` is null and private/runtime authorization remains false.
- `--check` independently recomputes evidence and rejects any pack, protocol, raw, or result change.
- Artifact tests assert measured counts and deterministic winner/null behavior.

## HIC-T6 — Complete Lite QA, documentation, and GitHub delivery

- [x] Verify the repository, write review/evidence/decision/log updates, install and test the CLI,
  then commit and push only Product Variant Resolver files. _(→HIC-R1–R11)_

Owner: QA and documentation responsibilities under the Lite task executor.

Files created or updated:

- `specs/human-knowledge-identity-contradiction-development/review.md`
- `docs/evidence/human-knowledge-identity-contradiction-development-v1.md`
- `docs/evidence/ai-evals/human-knowledge-identity-contradiction-v1.md`
- `docs/decisions/product-variant-resolver.md`
- `docs/PROJECT-LOG.md`
- `docs/REAL-CATALOG-ROADMAP.md`
- `README.md`

Acceptance:

- Focused tests, complete repository tests, targeted Ruff/format, MyPy, compile, installed CLI,
  repeated integrity checks, and `git diff --check` pass.
- Review maps HIC-R1–R11 to evidence and distinguishes implementation quality from product-policy
  eligibility.
- Project Log explains the problem, changed code, technical choices, result, failure mode, and next
  gate in narrative form.
- No runtime/API/PostgreSQL/canonical/release/color behavior changes.
- Commit contains no workspace-level agent/config files and GitHub `main` matches the local commit.

## Execution checkpoint

No task is approved for implementation until the owner confirms this task list. After confirmation,
execution begins with HIC-T1 only; later tasks advance in order after their acceptance checks pass.
