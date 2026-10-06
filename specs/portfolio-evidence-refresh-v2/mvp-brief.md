# Portfolio evidence refresh v2 — MVP brief

Date: 2026-10-05. Mode: Lite / Lean Industrial. Status: **complete**.

## Purpose

Refresh the repository landing page and interview guide after the real-catalog ranking, no-match
holdout and balanced policy evaluations. Preserve the original fixture experiment as history, but
replace its former headline position with the strongest current evidence and its runtime-HOLD
limitation. This milestone changes documentation only.

## Observable requirements

- **PER-R1 — Current scope.** WHEN README opens, THE DOCUMENTATION SHALL disclose the frozen
  1,763-release third-party snapshot, 153 image-search-derived positive queries and independent
  20-query catalog-relative no-match holdout before presenting metrics.
- **PER-R2 — Dual-RAG architecture.** The architecture SHALL show canonical candidate retrieval,
  optional local Pointwise reranking, frozen calibration/policy, three outcomes and the separate
  non-authoritative Human Knowledge branch. It SHALL state that no LLM generates the answer.
- **PER-R3 — Ranking evidence.** README SHALL report the frozen 53-case RRF/heuristic/Pointwise/
  Listwise comparison with exact denominators and identify Pointwise's `36/53` exact Top-1 versus
  RRF `29/53` without calling it runtime performance.
- **PER-R4 — Policy evidence.** README SHALL report `5/5` accepted positive exact precision,
  `5/53` positive exact recall, `3/53` false no-match, `11/20` negative no-match, `0/20` negative
  false matches and `54/73` combined abstention. Runtime SHALL be described as HOLD.
- **PER-R5 — Historical integrity.** The saturated fixture `winner: null` result SHALL remain linked
  and SHALL be explained as the reason a harder benchmark was built, not silently replaced.
- **PER-R6 — Honest limitations.** Third-party authority, image-search-derived queries, positive
  prior ranking use, low calibrated coverage, non-neural default similarity and absent production
  scale/generalization SHALL remain visible.
- **PER-R7 — Interview support.** `docs/PORTFOLIO-GUIDE.md` SHALL contain exactly three current
  resume bullets, one current 60–90 second pitch, a four-step code-review path, claim guardrails,
  the technical stack rationale and an honest next-step statement.
- **PER-R8 — Evidence navigation.** Every new metric and architecture claim SHALL link to a tracked
  dataset, result, QA review or evidence file; all repository-relative links SHALL resolve.
- **PER-R9 — Documentation-only boundary.** No source code, API, dependency, data, model, threshold,
  runtime configuration or evaluation artifact SHALL change.
- **PER-R10 — Project Log.** The log SHALL explain the communication problem, changed sections,
  why newer evidence replaces the fixture as headline, and why high precision is shown together
  with recall/abstention and runtime HOLD.

## Design and decision

README remains an English recruiter/technical-interviewer landing page. It keeps the stable
problem-first entity-resolution framing and Dual-RAG authority explanation, but reorganizes measured
evidence into release ranking and calibrated policy subsections. The first neural fixture remains a
short research-history paragraph. Detailed hashes, protocols and row governance stay in linked
artifacts rather than expanding the landing page.

The Portfolio Guide is rewritten around exactly three defensible bullets: measured ranking gain,
governed calibrated evaluation, and the Dual-RAG/provenance/storage boundary. Its pitch explicitly
pairs 100% accepted precision with 73.97% abstention so interview language cannot hide coverage.

## Tasks

- [x] **PER-T1** Refresh README scope, architecture and authority narrative. _(→PER-R1–R2)_
- [x] **PER-T2** Publish current ranking/policy tables and preserve the fixture history. _(→PER-R3–R6)_
- [x] **PER-T3** Rewrite the three-bullet Portfolio Guide and review path. _(→PER-R7)_
- [x] **PER-T4** Validate metrics, links, terminology and documentation-only scope. _(→PER-R8–R9)_
- [x] **PER-T5** Record QA, decision rationale and Project Log. _(→PER-R10)_

## Acceptance

README and Portfolio Guide metrics must equal the frozen JSON artifacts; the guide must have exactly
three resume bullets; all local links must resolve; runtime HOLD and 73.97% abstention must remain
visible; the diff must be documentation/spec-only and `git diff --check` must pass.
