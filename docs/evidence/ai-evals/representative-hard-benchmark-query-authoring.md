# AI artifact evaluation — RHB-T5 output-blind query authoring

Date: 2026-10-04
Scope: private 60-case query artifact, public aggregate manifest and authoring lifecycle
Verdict: **PASS WITH DATA-GATE SHORTFALLS — SAFE ARTIFACT, NOT A REPRESENTATIVE BENCHMARK**

| Rubric | Result | Evidence and boundary |
|---|---|---|
| Output blindness | PASS | Fresh independent agent received only the query projection; recorded flags prohibit output, label, failure-category and split access. |
| Authorization | PASS | Private self-binding ledger matches the exact RHB-T5 response and explicitly denies RHB-T6, RHB-T7 and resolver evaluation. |
| Non-synthetic composition | PASS | Exactly 60 unique queries, source references and evidence events were selected from the approved real-query projection. |
| Publication privacy | PASS | Raw rows and owner text remain in ignored `0600` files; public Git contains hashes and aggregates only. |
| Label leakage | PASS | Pack contains no expected status/UUID, correctness, rank, failure type or split and declares output unseen. |
| Determinism and atomicity | PASS | Check replay is unchanged; partial second-output replacement rolls both outputs back. |
| Challenge semantics | PASS after correction | Query-only `unknown_to_catalog` inference is prohibited; same-casting tags require a repeated family group. |
| Challenge coverage | BLOCKED | Published shortfalls remain for year, color, series, identifier and unknown-to-catalog. |
| Claim calibration | PASS | Pack sets `representative_pilot=false`; documents call it an authoring/provenance artifact only. |
| Downstream authority | PASS | No labels, split or evaluation were created; no authorization is inferred for RHB-T6/RHB-T7. |

## QA correction captured

The first authoring draft overinterpreted query text: it treated catalog-relative absence as a
surface property and counted same-casting tags without requiring repeated family rows. It also
coupled tracked code to verbatim private authorization text. Independent QA rejected those choices.
The corrected implementation keeps only a public authorization hash, prohibits
`unknown_to_catalog` at T5, validates same-family multiplicity, labels every count provisional and
publishes exact shortfalls.

This evaluation fails if private rows enter Git, an owner response appears in a tracked file, a
query-only tag is presented as an owner-verified outcome, shortfalls are padded with synthetic or
duplicate cases, `representative_pilot` becomes true, or any downstream label/split/evaluation is
created without a separate Owner Gate.
