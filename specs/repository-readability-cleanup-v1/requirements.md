# Repository Readability Cleanup v1 — Requirements

Mode: **Lite / Lean Industrial**  
Source: Repository Readability & Portfolio Cleanup PRD  
Scope: presentation, organization, terminology, documentation quality, and active-core static quality only.

## Requirements

### R1 — Portfolio landing page

WHEN a new reader opens the repository README, THE SYSTEM SHALL identify the project as
**Confidence-Aware Product Entity Resolution & Learning-to-Rank**, explain the problem and scope,
and expose a short path to architecture, results, code, limitations, and deeper evidence.

### R2 — Public terminology

WHEN public-facing documentation describes the two retrieval corpora, THE SYSTEM SHALL use
**authority-separated dual-corpus retrieval** and SHALL NOT position the project as RAG or
Dual-RAG. WHEN `hashing-v1` is described, THE SYSTEM SHALL identify it as deterministic,
hashing-based similarity rather than a learned neural embedding.

### R3 — Result hierarchy

WHEN the README presents ranking evidence, THE SYSTEM SHALL use the paired dual-source final as
the only portfolio headline: exact-release Top-1 `55% → 64%`, casting Top-1 `86% → 95%`, MRR@10
`0.722 → 0.792`, and Recall@25 `99% → 99%`, with the denominator stated as 100 observations from
50 held-out identities. Historical and negative results SHALL remain accessible outside the README.

### R4 — Three-layer information architecture

WHEN a reader wants more detail, THE SYSTEM SHALL provide the path README landing page → technical
overview/index → deep evidence. `docs/README.md`, `docs/CODE-TOUR.md`, `docs/RESULTS.md`,
`docs/LIMITATIONS.md`, an architecture overview, and a historical archive entry SHALL exist.

### R5 — Portfolio guide consistency

WHEN resume or interview claims are prepared from `docs/PORTFOLIO-GUIDE.md`, THE SYSTEM SHALL use
the same positioning, primary result, denominator, scope boundary, and non-deployment language as
the README.

### R6 — Architecture readability

WHEN the architecture is inspected, THE SYSTEM SHALL show candidate retrieval, RRF fusion,
Pointwise cross-encoder reranking, calibration, abstention, and the non-authoritative Human
Knowledge branch, including why each component exists.

### R7 — Artifact transparency

WHEN a reviewer inspects repository size, THE SYSTEM SHALL document which artifacts are committed,
generated, local-only, or reconstructible, and SHALL inventory the retained large checkpoints and
reports without deleting frozen evidence.

### R8 — Active-core static quality

WHEN Ruff and strict MyPy run on `retrieval.py`, `rerank.py`, `calibration.py`, `policy.py`,
`service.py`, and `api.py`, THE SYSTEM SHALL report zero findings. The change SHALL NOT alter the
resolver's decisions, model selection, thresholds, data membership, or runtime defaults.

### R9 — Documentation drift protection

WHEN documentation tests run, THE SYSTEM SHALL verify the headline values against the frozen
result JSON, reject primary Dual-RAG wording, enforce the paired denominator disclosure, and verify
that local Markdown links in the public reading path resolve.

### R10 — Historical preservation and scope

IF a file is frozen historical evidence, THEN THE SYSTEM SHALL retain it unchanged and foreground
it only through archive/deep-evidence navigation. This cleanup SHALL NOT add or train models, rerun
holdouts, modify frozen metrics, change canonical authority, or activate a runtime policy.

### R11 — Traceable delivery

WHEN the cleanup is complete, THE SYSTEM SHALL record design choices, verification results, known
limitations, and deferred P2 work in the decision log, Project Log, review, and evidence documents.

