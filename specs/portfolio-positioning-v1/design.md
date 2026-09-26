# Portfolio positioning and README restructure v1 — Design

Date: 2026-09-26. Mode: Lite / Lean Industrial. Status: **READY FOR IMPLEMENTATION REVIEW**.

## 1. Overview

This milestone changes the repository's communication hierarchy, not the product. The current
README is approximately 1,079 lines and contains high-value technical evidence mixed with detailed
review batches, adjudication history, checksums, staging narratives, and validation chronology. The
new README will act as a recruiter-facing landing page; evidence-heavy material will remain in the
existing `docs/`, `reports/`, `specs/`, and source-data documentation and will be reachable through a
curated deep-evidence index.

The primary positioning becomes:

> Product Variant Resolver — Confidence-Aware Product Entity Resolution for Noisy Marketplace
> Listings

The supporting one-line description is:

> Maps noisy marketplace titles to canonical product variants using hybrid retrieval, structured
> evidence, calibrated abstention, and a provenance-aware human-review boundary.

`Dual RAG` remains accurate as an internal two-corpus retrieval description, but it moves from the
headline to the architecture/trust-boundary explanation because the system solves entity resolution
rather than retrieval-augmented text generation.

## 2. Documentation architecture

```text
README.md                              recruiter / first technical read
    |
    +-- docs/PORTFOLIO-GUIDE.md        resume bullets + 60–90 second pitch
    +-- docs/evidence/*                public technical evidence
    +-- reports/*                      measured and machine-readable results
    +-- specs/*                        requirements, design, tasks, QA reviews
    +-- data/* documentation           provenance and source-specific review
    +-- docs/PROJECT-LOG.md            chronological engineering rationale
```

The README owns the short, stable narrative. It does not duplicate complete audit trails. The deeper
artifacts remain the source of truth for exact protocols, checksums, decision history, and row-level
review.

## 3. README information design

### 3.1 Hero and scope

The opening block contains:

1. project name;
2. confidence-aware entity-resolution subtitle;
3. one-line problem/solution statement;
4. a short disclosure that current headline evidence is fixture validation, not production or
   marketplace coverage;
5. quick links to architecture, evaluation, local run, limitations, and deep evidence.

It must not lead with RAG, FastAPI, PostgreSQL, pgvector, MiniLM, or a technology list.

### 3.2 Problem

Use a short marketplace example to explain that casting names alone are insufficient and that year,
color, series, and collector number can distinguish variants while seller metadata may be wrong or
missing. State the asymmetric risk: a false canonical match may be worse than returning
`ambiguous` or `no_match`.

### 3.3 Architecture

Use one compact diagram and a short explanation:

```text
noisy marketplace title
          |
   signal extraction
          |
 sparse + hashing similarity + structured evidence
          |
        RRF
          |
 confidence calibration + decision policy
          |
 matched | ambiguous | no_match

Human Knowledge retrieval --------> explanation/review evidence only
                                     never canonical UUID authority
```

The diagram must label `hashing-v1` as non-neural. PostgreSQL may be presented as an optional
retrieval/storage path, not as the definition of the system.

### 3.4 Key engineering decisions

Keep this section to the decisions that explain system value:

- soft structured conflicts prevent noisy seller metadata from prematurely deleting the correct
  candidate;
- RRF combines heterogeneous rankers without pretending their raw scores share a scale;
- calibrated abstention makes false-match risk explicit;
- Human Knowledge and canonical identity have separate authority;
- measured neural complexity was rejected when it produced no incremental ranking value.

### 3.5 Measured evaluation

Reuse checked-in values without recomputation. Every perfect metric must show its scope and
denominator. The section should lead with a disclosure such as:

> Fixture evidence: 100 synthetic/curated cases, 120 catalog products; Test contains 21 cases and
> 12 matched ranking targets. These measurements do not establish production accuracy.

The compact table may include Recall@25, Top-1, hard-negative accuracy, precision, false-match rate,
coverage, and the current latency evidence, but it must link to the versioned report and QA review.

### 3.6 Neural comparison

Preserve one three-arm table and the exact interpretation:

| Arm | Top-1 | Resolver p95 | Runtime status |
|---|---:|---:|---|
| RRF | `12/12` | `1.398 ms` | default |
| Neural pointwise | `12/12` | `89.164 ms` | shadow only |
| Neural listwise | `12/12` | `89.583 ms` | shadow only |

The text states `winner: null`, approximately 64× p95 latency for no Top-1 gain, a saturated fixture
baseline, and no universal claim against neural reranking. It links to the comparison report, public
evidence, and QA review.

### 3.7 Limitations

State the limitations directly:

- synthetic/curated fixture and small matched Test denominator;
- saturated RRF baseline limits conclusions about incremental retrieval/reranking value;
- `hashing-v1` is not a learned neural semantic embedding;
- large-catalog, production-concurrency, and real-marketplace generality are not established;
- real-world benchmark and risk/coverage evaluation are deferred follow-up work.

### 3.8 Run locally

Keep only the core editable install, Uvicorn start, one `/resolve` request and one `/health` request.
Link to deeper runbooks, PostgreSQL evidence, Docker status, or test commands as appropriate. Avoid
putting historical execution narration in this section.

### 3.9 Deep evidence

Use a small categorized table rather than chronological prose. Each category gets a one-sentence
scope and one or more repository-relative links.

| Category | Minimum destination |
|---|---|
| Core MVP and QA | `specs/product-variant-resolver/mvp-brief.md`, `specs/product-variant-resolver/review.md`, `docs/evidence/product-variant-resolver-mvp.md` |
| Neural comparison | `reports/neural-reranker-comparison-v1/comparison.md`, `docs/evidence/neural-reranker-comparison-v1.md`, `specs/neural-reranker-comparison/review.md` |
| Human Knowledge | relevant Human Knowledge specs and `docs/evidence/` index entries |
| External/review-only catalog work | source-specific README plus the Fandom/release evidence artifacts |
| PostgreSQL and storage | PostgreSQL/storage specs, evidence, and runbook links |
| Engineering history | `docs/PROJECT-LOG.md`, `docs/decisions/product-variant-resolver.md` |

Before deleting any detailed README subsection, the implementer must confirm that its material is
represented by at least one existing deep-evidence destination. If not, the detail stays in the
README until the documentation owner assigns a durable destination.

## 4. Core reader flows

### Recruiter / first-time visitor

Open the repository, read the hero, problem, architecture, decisions, measured result and limitations
without following a link. The reader should understand that the project is an entity resolver that
can abstain, not a generative chatbot.

### Technical interviewer

Start from the same narrative, then follow a deep-evidence link to inspect exact denominators,
protocols, QA, checksums or design rationale. The linked artifact—not a compressed README sentence—
remains authoritative for implementation detail.

### Project owner preparing an interview

Open `docs/PORTFOLIO-GUIDE.md`, select the three evidence-backed bullets, and rehearse the 60–90
second pitch. The claim guardrails show which stronger claims must wait for a real-world benchmark.

## 5. Frontend/backend boundaries

This work has no application frontend or backend implementation. `README.md` is the public landing
surface, `docs/PORTFOLIO-GUIDE.md` is interview support, and `docs/PROJECT-LOG.md` is the historical
record. Files under `src/`, `ui/`, `migrations/`, `data/`, `config/`, `constraints/`, and runtime
artifact directories are read-only inputs to this milestone.

## 6. Tech stack assumptions

- GitHub-flavored Markdown is the rendering target; diagrams must remain readable as plain text or
  use GitHub-supported syntax.
- Repository-relative links are preferred so forks and local checkouts remain navigable.
- Existing Markdown/JSON reports are the source of measured values; this milestone does not run a
  new model or produce replacement metrics.
- No documentation framework, JavaScript site generator, external badge service, or hosted analytics
  is introduced.
- English remains the public README and portfolio-guide language because the current repository is
  written for an international AI Engineer / SWE audience. The Project Log may retain its existing
  Chinese explanatory style.

## 7. Interfaces and content contracts

No API contract changes. Documentation must retain these verified external names:

- endpoint examples: `POST /resolve`, `GET /health`;
- response decisions: `matched`, `ambiguous`, `no_match`;
- canonical authority: canonical catalog only;
- default fusion: RRF;
- default similarity representation: deterministic `hashing-v1`, non-neural;
- neural result: `winner: null`, shadow-only, RRF unchanged.

Relative Markdown links are the only new integration interface. They must resolve from the file in
which they appear and use repository-relative paths suitable for GitHub.

## 8. Data model

This milestone introduces no product data model. It uses a small documentation claim model:

```text
Claim
  statement              reader-facing sentence or metric
  scope                   fixture / Test / runtime / shadow experiment
  numerator_denominator   required for perfect result where applicable
  evidence_link           checked-in source of truth
  limitation              what the evidence does not establish
```

The portfolio guide uses the same claim model so resume bullets and the interview pitch cannot
silently broaden README evidence.

## 9. Error handling

- If a target evidence link is missing, keep the relevant README detail and fail PP-R10/PP-R16
  rather than publish an orphaned summary.
- If two checked-in artifacts disagree on a value, use the immutable measured report as the source
  of truth, record the conflict in QA, and do not guess.
- If a resume sentence cannot be traced to current evidence, omit it or label it as a future example.
- If shortening removes a necessary warning or limitation, restore it before approval.
- If a product-code or data diff appears, fail the documentation-only safety gate.

## 10. Basic security and integrity notes

The rewrite must not copy secrets, local absolute paths, private source data, ignored model weights,
or owner-only working files into the public README. It must preserve the existing rule that raw
marketplace titles are omitted from resolution logs and must not imply that review-only data has
canonical authority. External-source licensing and provenance remain linked to their existing
source documentation rather than summarized into a new legal claim.

## 11. Portfolio guide design

Create `docs/PORTFOLIO-GUIDE.md` with:

1. **Positioning:** the headline and one-line project explanation;
2. **Three current-evidence bullets:** core resolver, trust/provenance boundary, and neural negative
   experiment;
3. **60–90 second pitch:** problem → architecture → authority boundary → neural experiment decision
   → current benchmark limitation and next research direction;
4. **Claim guardrails:** phrases that are currently accurate and phrases that require a future
   real-world benchmark;
5. **Future metric template:** explicitly marked as an example that must not be used until its values
   are measured.

This file is the durable landing point for resume/interview material; the README links to it but does
not duplicate the full pitch.

## 12. Testing strategy

### Static content checks

- Confirm the required README section order.
- Search for `hashing-v1`, `neural`, `embedding`, `RAG`, `100%`, `production`, `winner`, and latency
  values; inspect every occurrence for correct scope.
- Confirm the README contains the exact fixture/Test denominators.
- Confirm the portfolio guide has exactly three present-tense/current-evidence bullets and one pitch.

### Link and evidence checks

- Parse local Markdown links from README and the portfolio guide and confirm every repository-local
  target exists.
- Compare metric values with `reports/fixture-v1/evaluation-fixture-v1-test.md` and
  `reports/neural-reranker-comparison-v1/comparison.md`.
- Map every former audit-heavy README category to at least one deep-evidence link.

### Scope checks

- `git diff --name-only` may include only `README.md`, `docs/PORTFOLIO-GUIDE.md`,
  `docs/PROJECT-LOG.md`, and `specs/portfolio-positioning-v1/*` for this milestone.
- No product tests are required for a Markdown-only change, but existing lightweight documentation
  or link checks should run if available.
- `git diff --check` must pass.

### Acceptance review

QA records a PP-R1–PP-R16 coverage table and PASS/FAIL verdict in
`specs/portfolio-positioning-v1/review.md`. The review must state that this is a presentation change,
not new product capability.

## 13. Key decision and trade-off

The design intentionally does not delete or rewrite deep engineering evidence. It changes navigation
and emphasis: the README presents the stable technical story, while specialized artifacts preserve
auditability. The trade-off is one extra click for reviewers seeking row-level detail; the benefit is
that a first-time reader can understand the project without scanning more than one thousand lines of
chronological execution history.
