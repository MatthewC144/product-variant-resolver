# Pointwise policy untouched-holdout readiness — MVP brief

Date: 2026-10-05. Mode: Lite / Lean Industrial. Status: **complete with data shortfall**.

## Purpose

Determine whether existing local real-query sources contain an independently untouched,
human-answered no-match holdout that can test the frozen Pointwise v2 three-state policy. This is a
readiness audit only; it does not score the resolver, inspect final-test outputs, retune thresholds or
authorize runtime activation.

## Observable requirements

- **PPHR-R1 — Frozen policy binding.** WHEN readiness is checked, THE SYSTEM SHALL bind the existing
  v2 calibration, policy and selection artifacts and SHALL require `runtime_eligible=false`.
- **PPHR-R2 — Source independence.** WHEN local sources are audited, THE SYSTEM SHALL count unique
  query IDs and overlap with the tracked 101-case human source without persisting row identifiers or
  content.
- **PPHR-R3 — Answer requirement.** A query SHALL count as holdout-eligible only if it is unused by
  v2, organic, has an independent human identity answer and is governed relative to the same frozen
  catalog.
- **PPHR-R4 — Permission boundary.** Existing RHB decisions SHALL NOT count when split, scoring and
  resolver evaluation remain unauthorized.
- **PPHR-R5 — Shortfall.** IF fewer than 20 eligible untouched no-match queries exist, THEN THE
  SYSTEM SHALL report the exact aggregate shortfall and SHALL NOT evaluate or activate the policy.
- **PPHR-R6 — Minimal public artifact.** The tracked result SHALL contain only hashes, counts,
  classifications, guardrails and the next gate; no external CSV, query, label or case ID is copied.

## Design and decision

The audit compares three sibling-project CSV sources to the 101 tracked case IDs. The 105-row human
queue contains the same 101 imported cases plus four excluded ambiguous rows with no human expected
identity. The 230 comparison rows and 1,640 evidence rows cover only tracked IDs and are derivatives,
not new queries. Consequently, all 52 labeled no-match candidates have already participated in v2
development fit or threshold selection.

RHB contains one owner-approved no-match aggregate, but its own governance says labels are not
materialized and split, scoring and resolver evaluation are false. It is recorded as potentially
relevant but ineligible, not silently repurposed.

## Tasks

- [x] **PPHR-T1** Audit case-ID overlap and human-answer completeness across existing local sources.
  _(→PPHR-R2–R3)_
- [x] **PPHR-T2** Bind the frozen v2 artifacts and RHB permission state. _(→PPHR-R1, R4)_
- [x] **PPHR-T3** Publish an aggregate-only 0/20 readiness result and explicit contract for new
  collection. _(→PPHR-R5–R6)_
- [x] **PPHR-T4** Add deterministic integrity and privacy tests. _(→PPHR-R1–R6)_
- [x] **PPHR-T5** Record the limitation and next owner gate in QA, decision history and Project Log.

## Acceptance

The audit must reproduce the same source hashes and aggregate counts, expose no row-level keys,
report zero eligible untouched no-match rows and a 20-row shortfall, read/score zero final-test rows,
leave runtime unchanged and refuse any changed source inventory.
