# Portfolio positioning and README restructure v1 — Requirements

Date: 2026-09-26. Mode: Lite / Lean Industrial. Status: **READY FOR IMPLEMENTATION REVIEW**.

## Product goal

Turn the repository homepage into a concise portfolio landing page for an AI Engineer / SWE
audience without changing, deleting, or overstating the underlying engineering evidence. The first
screen and primary narrative must frame Product Variant Resolver as a **confidence-aware product
entity-resolution system**, while the existing Dual-RAG implementation remains an accurately
described internal architecture detail.

The outcome should let a recruiter or interviewer answer these questions in roughly two minutes:

1. What problem does the project solve?
2. What is technically interesting about the architecture?
3. What measured result and engineering decision does the evidence support?
4. What are the current limitations?
5. Where can a technical reviewer inspect the deeper evidence?

## Requirements

### PP-R1 — Entity-resolution headline

WHEN the repository README is rendered, THE DOCUMENTATION SHALL present `Product Variant Resolver`
as a **confidence-aware product entity-resolution system** for mapping noisy marketplace listings to
canonical product variants, and SHALL NOT use `Dual RAG`, `RAG`, an LLM, or a vector database as the
primary headline.

### PP-R2 — Problem and user-visible outcome

WHEN a reader opens the README, THE DOCUMENTATION SHALL explain before setup instructions that
marketplace titles are noisy, near-identical variants require multiple evidence types, and a wrong
confident match can be worse than abstaining. It SHALL name the three observable outcomes exactly as
`matched`, `ambiguous`, and `no_match`.

### PP-R3 — Truthful runtime architecture

WHEN the README describes the resolver flow, THE DOCUMENTATION SHALL show the existing runtime path
as signal extraction followed by sparse, similarity-based, and structured retrieval; RRF candidate
fusion; confidence calibration; and the decision policy. It SHALL state that structured conflicts
are soft evidence rather than hard filters and that only the canonical catalog branch may produce a
canonical UUID.

### PP-R4 — Human Knowledge authority boundary

WHEN Human Knowledge is introduced, THE DOCUMENTATION SHALL describe it as a separate retrieval and
review-evidence branch that can support explanation and debugging but cannot silently create or
replace a canonical identity. It MAY identify this internal separation as the project's Dual-RAG
architecture, but SHALL NOT imply that an LLM generates the final answer.

### PP-R5 — Accurate `hashing-v1` terminology

WHEN `hashing-v1` is mentioned, THE DOCUMENTATION SHALL identify it as a deterministic,
hashing-based similarity representation or baseline and SHALL explicitly state that it is **not a
learned neural embedding model**. It SHALL NOT describe the default runtime as neural semantic
retrieval, Sentence Transformer retrieval, MiniLM retrieval, or LLM-powered retrieval.

### PP-R6 — Neural experiment boundary

WHEN MiniLM, pointwise reranking, or listwise reranking is mentioned, THE DOCUMENTATION SHALL identify
it as an isolated, offline shadow comparison over the same frozen Top-25 canonical candidate pools.
It SHALL state that neither neural arm is active in the FastAPI runtime and that RRF remains the
runtime default.

### PP-R7 — Preserve the negative experiment

WHEN the neural comparison result is summarized, THE DOCUMENTATION SHALL preserve the measured null
result: RRF, neural pointwise, and neural listwise each achieved `12/12` Top-1 on the matched Test
denominator; resolver p95 was approximately `1.398 ms`, `89.164 ms`, and `89.583 ms`; the declared
result was `winner: null`; and the neural arms added no ranking gain. The summary SHALL explain that
the fixture baseline was already saturated and SHALL NOT generalize the result into a claim that
neural reranking is universally ineffective.

### PP-R8 — Scoped evaluation claims

WHEN the README displays evaluation metrics, THE DOCUMENTATION SHALL disclose that the headline
evidence comes from a 100-case synthetic/curated benchmark backed by a 120-product fixture catalog,
with 21 Test cases and 12 matched ranking targets. Any `1.0`, `100%`, or perfect-count result SHALL
appear with its denominator and fixture limitation; it SHALL NOT be presented as production,
marketplace, or statistically general accuracy.

### PP-R9 — Visible limitations

WHEN a reader reviews the portfolio page, THE DOCUMENTATION SHALL provide a dedicated limitations
section that names the small synthetic/curated fixture, benchmark saturation, limited scale and
production-concurrency evidence, default non-neural similarity representation, and the absence of
real-marketplace generality.

### PP-R10 — Preserve deep evidence through links

WHEN detailed batch histories, adjudication notes, checksums, staging audits, PostgreSQL evidence,
or validation histories are removed from the main README narrative, THE DOCUMENTATION SHALL retain
their existing repository artifacts and SHALL replace the removed narrative with concise links to
the relevant `docs/`, `reports/`, `specs/`, or data-source documentation. No evidence file SHALL be
deleted, rewritten as a stronger claim, or made unreachable from the README's deep-evidence index.

### PP-R11 — Portfolio landing-page structure

WHEN the README restructure is complete, THE DOCUMENTATION SHALL present, in this order: hero and
scope disclosure; problem; architecture; key engineering decisions; measured evaluation; neural
comparison; limitations; minimal local-run instructions; and deep-evidence links. Detailed
chronological audit narratives SHALL remain outside this primary reading path.

### PP-R12 — Resume bullets and interview pitch

WHEN portfolio support material is published, THE DOCUMENTATION SHALL add
`docs/PORTFOLIO-GUIDE.md` containing exactly three current-evidence resume bullets—core resolver,
canonical/Human-Knowledge authority boundary, and neural comparison—and one 60–90 second interview
pitch. The guide SHALL distinguish currently measured claims from a clearly labeled future example
that may be used only after a representative real-world benchmark exists.

### PP-R13 — Minimal setup remains usable

WHEN the README is shortened, THE DOCUMENTATION SHALL preserve a minimal offline installation,
server-start, `/resolve`, and `/health` example, and SHALL link to deeper operational or PostgreSQL
instructions rather than reproducing their complete history on the landing page.

### PP-R14 — Project Log traceability

WHEN this portfolio-positioning work is completed, THE DOCUMENTATION SHALL append an entry to
`docs/PROJECT-LOG.md` that explains (1) what was changed and which communication problem it solves,
(2) which documentation sections/files changed, (3) why entity resolution replaced RAG as the
headline while Dual RAG remained an architectural detail, and (4) why evidence was linked rather
than deleted.

### PP-R15 — Documentation-only safety boundary

WHILE this milestone is implemented, THE SYSTEM SHALL NOT change product code, API schemas,
retrieval behavior, candidate ranking, calibration, policy thresholds, data, database migrations,
runtime dependencies, neural artifacts, or test fixtures. Documentation SHALL describe the current
verified system rather than introduce a new runtime promise.

### PP-R16 — Verifiable consistency

WHEN the milestone is reviewed, THE DOCUMENTATION SHALL have valid relative links, internally
consistent denominators and latency values, no unsupported production claim, no default-runtime
neural-embedding claim, and no product-code diff. A QA review SHALL map every PP requirement to a
check and record PASS or FAIL in `specs/portfolio-positioning-v1/review.md`.

## MVP scope

- Reframe the README headline and first-screen narrative around confidence-aware entity resolution.
- Convert the README into a concise portfolio landing page using the existing measured evidence.
- Clarify the default hashing-based similarity representation and the isolated neural experiment.
- Preserve the neural null result and its benchmark limitations.
- Replace detailed audit narration with a curated deep-evidence link index without deleting source
  artifacts.
- Add current-evidence resume bullets and a 60–90 second interview pitch.
- Append the required Project Log entry and create a requirement-mapped QA review.

## Out of scope / deferred

- Building the P1 real-marketplace benchmark, hard negatives, failure taxonomy, risk/coverage
  curves, calibration analysis, or scale tests.
- Changing the resolver, FastAPI, PostgreSQL, pgvector, Docker, observability, model, or runtime.
- Promoting Human Knowledge or review-only data into canonical identity.
- Re-running, retuning, or replacing the completed neural comparison.
- Adding an LLM, GraphRAG, multi-agent workflow, another embedding model, or a new reranker.
- Claiming production readiness, real-marketplace accuracy, or statistical generality.

## Source basis

This specification is grounded in the current README, the canonical MVP specification and QA
evidence, the immutable neural-comparison artifacts, the project decision record and Project Log,
and the owner-supplied AI Engineer / SWE assessment dated 2026-09-26. The external assessment guides
presentation priorities but does not override checked-in measured evidence.
