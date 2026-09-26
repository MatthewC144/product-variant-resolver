# Portfolio positioning and README restructure v1 — Tasks

Date: 2026-09-26. Mode: Lite / Lean Industrial. Status: **COMPLETE**.

Each task is documentation-only, independently reviewable, and must preserve edits made by other
collaborators. No task may modify product code, data, runtime configuration, dependencies, model
artifacts, or database migrations.

- [x] **PP-T1 — Create the portfolio/interview guide.** _(→PP-R1, PP-R5, PP-R6, PP-R7, PP-R8, PP-R9, PP-R12)_

  **Changes:** Create `docs/PORTFOLIO-GUIDE.md` with the approved positioning, exactly three
  current-evidence resume bullets, one 60–90 second pitch, claim guardrails, and a clearly labeled
  future-metric template. Keep `hashing-v1`, the shadow-only neural experiment, fixture denominators,
  `winner: null`, and limitations accurate.

  **Files:** `docs/PORTFOLIO-GUIDE.md`.

  **Acceptance:** The guide contains the five design sections; has exactly three current-evidence
  bullets; the pitch covers problem, architecture, authority boundary, model-selection decision and
  limitation; every measured claim maps to a checked-in report; no future example is phrased as a
  current result.

  **Suggested agent:** `doc_curator` (content curation; no product code).

- [x] **PP-T2 — Rewrite the README's portfolio narrative and architecture.** _(→PP-R1, PP-R2, PP-R3, PP-R4, PP-R5, PP-R11, PP-R15)_

  **Changes:** Replace the opening and architecture narrative with the entity-resolution headline,
  problem statement, compact architecture diagram, and key engineering decisions. Move Dual RAG
  below the headline and explain it as a canonical-versus-Human-Knowledge retrieval boundary. Label
  `hashing-v1` as a deterministic non-neural similarity representation.

  **Files:** `README.md`.

  **Acceptance:** A reader can identify problem, architecture, outcomes and authority boundary before
  setup instructions; all PP-R1–PP-R5 terms are present and consistent; the default runtime is not
  described as neural or LLM-generated; no application file changes.

  **Suggested agent:** `task_executor` for controlled documentation editing, with `doc_curator`
  consultation if needed.

- [x] **PP-T3 — Condense results, limitations, setup and deep evidence.** _(→PP-R6, PP-R7, PP-R8, PP-R9, PP-R10, PP-R11, PP-R13, PP-R15)_

  **Changes:** Keep compact fixture and three-arm neural tables with exact denominators, values,
  `winner: null`, and limitations. Preserve minimal offline run/API examples. Replace the long
  review-batch, adjudication, checksum, staging, PostgreSQL and validation narratives with a
  categorized deep-evidence index after confirming a durable destination for each category. Add a
  link to `docs/PORTFOLIO-GUIDE.md`; do not delete any underlying artifact.

  **Files:** `README.md`.

  **Acceptance:** Neural values match the immutable comparison report; every perfect metric has
  scope/denominator; limitations are visible; local start and two endpoint examples remain usable;
  each removed audit category has at least one valid repository link; no evidence file or product
  behavior is changed.

  **Suggested agent:** `task_executor` for README restructuring; `doc_curator` validates evidence
  destinations.

- [x] **PP-T4 — Record the documentation decision in the Project Log.** _(→PP-R10, PP-R14, PP-R15)_

  **Changes:** Append one entry to `docs/PROJECT-LOG.md` explaining what changed, the communication
  problem solved, the precise documentation surfaces modified, why entity resolution is the
  headline, why Dual RAG remains an architectural detail, why `hashing-v1` wording changed, and why
  deep evidence was linked rather than deleted.

  **Files:** `docs/PROJECT-LOG.md`.

  **Acceptance:** The entry contains the user's required four-part rationale, does not claim product
  behavior changed, and links the new portfolio guide and this spec.

  **Suggested agent:** `doc_curator`.

- [x] **PP-T5 — Run documentation QA and publish the requirement trace.** _(→PP-R1–PP-R16)_

  **Changes:** Validate heading order, terminology, exact metrics, denominators, limitations, local
  links, audit-category coverage, allowed-file scope and whitespace. Create a requirement-to-check
  table and PASS/FAIL verdict.

  **Files:** `specs/portfolio-positioning-v1/review.md` only, except for narrowly scoped corrections
  to milestone documentation discovered during QA.

  **Acceptance:** All local Markdown targets exist; metric values match the two checked-in measured
  reports; searches find no unsupported production claim or default-runtime neural-embedding claim;
  `git diff --check` passes; the diff contains no `src/`, `ui/`, `data/`, `migrations/`, dependency,
  model, or runtime changes; PP-R1–PP-R16 each have evidence and a result; overall verdict is PASS
  before the milestone is marked complete.

  **Suggested agent:** `qa`.

## Execution order and Lite gate

Execute PP-T1 → PP-T2 → PP-T3 → PP-T4 → PP-T5. PP-T2 and PP-T3 both edit README and therefore must
run sequentially rather than in parallel. The milestone passes the Lean G2/G3 documentation gate
only when all tasks are checked, QA is PASS, the Project Log is updated, and the working diff remains
documentation-only.
