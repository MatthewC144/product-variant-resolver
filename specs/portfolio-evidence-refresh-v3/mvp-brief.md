# Portfolio evidence refresh v3 — MVP brief

Date: 2026-10-10. Mode: Lite / Lean Industrial. Status: **complete**.

## Purpose

Expose the completed dual-source Serper benchmark in the repository landing page and interview
guide without conflating offline ranking evidence with calibrated-policy or runtime evidence. This
milestone changes documentation only.

## Observable requirements

- **PER3-R1 — Current benchmark scope.** README SHALL disclose 150 independent target identities,
  300 paired Image/Lens and Shopping records, and the grouped 100-development/50-final split.
- **PER3-R2 — Exact final claims.** README and Portfolio Guide SHALL report combined RRF-to-Pointwise
  changes of exact Top-1 `55% → 64%`, casting Top-1 `86% → 95%`, MRR@10 `0.722 → 0.792`, Recall@10
  `99% → 98%`, and unchanged Recall@25 at 99%.
- **PER3-R3 — Denominator honesty.** The final combined denominator SHALL be described as 100 source
  observations from 50 identities, never as 100 independent products.
- **PER3-R4 — Evidence separation.** Ranking evidence SHALL remain separate from the prior
  53-positive/20-negative policy evidence; runtime SHALL remain HOLD and the newer final test SHALL
  not authorize policy claims or tuning.
- **PER3-R5 — Interview support.** Portfolio Guide SHALL retain exactly three primary resume bullets,
  a current pitch, an evidence-led code-review path, claim guardrails and honest next steps.
- **PER3-R6 — Traceability.** New claims SHALL link to tracked frozen JSON, QA or AI-eval evidence and
  every repository-relative link SHALL resolve.
- **PER3-R7 — Documentation-only boundary.** Source, data, model, thresholds, dependencies,
  evaluation artifacts and runtime SHALL not change.
- **PER3-R8 — Project Log.** The log SHALL explain what communication gap was fixed, which documents
  changed, why paired denominators and negative metrics are shown, and why runtime remains held.

## Design and decision

The README keeps the problem-and-architecture narrative, then promotes dual-source evidence to the
first evaluation subsection. The Portfolio Guide leads with the new benchmark but preserves the
older calibrated-policy evidence as a distinct second bullet. This is more useful for a portfolio
than replacing one headline number with another: the reader can see both neural ranking value and
deployment discipline.

The final-test rows are paired measurements. Reporting `n=100` is valid for source observations, but
the underlying product-identity sample size remains 50. The one-point combined Recall@10 regression
is displayed beside Top-1 and MRR gains so the result cannot be read as universal dominance.

## Tasks

- [x] **PER3-T1** Refresh README scope, architecture, dual-source tables and limitations. _(→R1–R4)_
- [x] **PER3-T2** Refresh Portfolio Guide bullets, pitch, review path and guardrails. _(→R2–R5)_
- [x] **PER3-T3** Verify metrics, denominators, links, scope and secret hygiene. _(→R2–R7)_
- [x] **PER3-T4** Record verification and decision rationale. _(→R8)_

## Acceptance

Displayed metrics must equal the frozen aggregate artifact; the guide must contain exactly three
primary resume bullets; all local links must resolve; the runtime HOLD and final-test no-retuning
boundary must remain visible; and the diff must be limited to Markdown documentation/specification.
