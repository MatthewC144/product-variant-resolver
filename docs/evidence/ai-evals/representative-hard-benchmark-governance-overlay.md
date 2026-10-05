# AI artifact evaluation — RHB-T6 governance overlay

Date: 2026-10-05
Scope: owner-approved versioned governance overlay and repaired readiness
Verdict: **PASS — EXACTLY BOUND, PRIVACY-SAFE AND NON-AUTHORIZING FOR LABELS**

| Rubric | Result | Evidence and boundary |
|---|---|---|
| Owner intent | PASS | Private `0600` ledger binds the exact response hash and permits only overlay materialization. |
| Query scope | PASS | Matched-label admission is limited to one 60-row query-pack SHA and maximum 20 rows. |
| Authority scope | PASS | Only 20 sorted IDs in one CAR authority SHA are admitted; the Wiki source is not promoted globally. |
| Identity safety | PASS | Every future matched label must bind an admitted authority ID and matching canonical UUID; Human evidence remains non-authoritative. |
| Claim calibration | PASS | No manufacturer/global truth or new color/edition verification is asserted. |
| Historical integrity | PASS | Frozen T1/T3 files are unchanged and remain the source-wide baseline. |
| Privacy | PASS | Public overlay contains hashes, IDs and aggregates only; raw owner response, query rows and labels remain absent. |
| Gate separation | PASS | Overlay, label authoring, split and evaluation are separate permissions; the last three remain false. |
| Reproducibility | PASS | Canonical overlay content hash is `7f3a87…7cbe`; repaired readiness hash is `0de130…767b`. |

This evaluation fails if a different query pack or authority bundle is accepted, if any non-allowlisted
authority ID becomes usable, if source-wide T1/T3 is silently rewritten, if a Human label creates a
UUID, or if readiness is treated as permission to author labels.
