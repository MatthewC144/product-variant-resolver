# RHB-T6 governance overlay evidence

Date: 2026-10-05
Mode: Lite / Lean Industrial
Verdict: **PASS — BUNDLE-SPECIFIC OVERLAY MATERIALIZED; LABELING STILL UNAUTHORIZED**

## What was implemented

The project owner approved the previously proposed governance repair, but only for materializing a
versioned overlay. The resulting `rhb-t6-governance-overlay-v1.json` grants two narrowly coupled
admissions:

1. `human-labeled-real-noisy-v1` may contribute at most 20 `matched` labels only inside query pack
   SHA-256 `97f7f0dd61cf619bb16b198778356d8ef53c7a504086f11542922f90706a858a`.
2. Those labels may use exact identity only from the 20 allowlisted authority IDs in CAR bundle
   SHA-256 `72c11aeb8db03267a8deca4f50eb09d89c2c423a7e9ca983f498f76e80553117`.

Every future matched label must be reviewed by `project_owner` and bind both the admitted authority
ID and its canonical UUID. Human evidence cannot create a UUID. The Wiki source is not promoted as a
whole, and the overlay makes no Mattel/manufacturer or global-truth claim. Color and edition remain
unverified/null.

## Persistence and privacy boundary

The exact owner response is stored only in the existing Git-ignored private directory with file mode
`0600`; the directory remains `0700`. The tracked overlay stores only response/authorization hashes,
public authority IDs, frozen parent hashes, safe aggregates and explicit negative authorizations.
It contains no raw query, source-row reference, label, expected UUID or owner-response text.

| Artifact | SHA-256 |
|---|---|
| Query pack | `97f7f0dd61cf619bb16b198778356d8ef53c7a504086f11542922f90706a858a` |
| CAR authority bundle | `72c11aeb8db03267a8deca4f50eb09d89c2c423a7e9ca983f498f76e80553117` |
| Governance proposal content | `e5d1d74233626dc715f253608d3ea05da8965b043e324255306523b3dffdf8de` |
| Overlay content | `7f3a87ea250f38245ba4ba376290c370f0ccc9d96fffadc9bf7f8c479da67cbe` |
| Overlay file | `9b8a7965ae568098ff42f83060fc01270b4a100fa0870be7900414b0b8169311` |
| Post-overlay readiness | `0de13006b7d18d4a6afc6c1a74997589e6870f0137dfe40bb58d484fada2767b` |

## Why an overlay was selected

Frozen T1/T3 accurately records the earlier source-wide decision: Human data cannot create exact
identity and the Wiki derivative was staging context. Later CAR review established only 20 exact
records, not the reliability of every Wiki row. Rewriting T1/T3 would erase the historical decision;
promoting the source globally would exceed the reviewed evidence. A parent-hash-bound overlay keeps
the exception proportional and forces any future expansion through another version and Owner Gate.

The core validators now accept the later CAR catalog-v2 authority only when the complete bundle and
overlay match. Without the overlay, the frozen source prohibition still fails closed. Machine IDs and
SHA evidence references are excluded from the public PII text scan because their digit sequences are
not personal contact data; human-facing reviewer text remains scanned.

## Repaired readiness and remaining boundary

RHB-T6 readiness now reports `ready_for_separate_owner_authorization`, effective matched capacity
`20`, permission shortfall `0`, and exact bundle admission valid. It also reports that frozen T1/T3
itself is still source-wide incompatible, that no labels exist, and that provisional challenge
shortfalls total `16`. Those challenge tags must be confirmed during owner review or the rows must be
held.

The overlay explicitly records that it did not itself authorize RHB-T6 label review, RHB-T7 or
resolver evaluation. A later, separately hash-bound Label Review v1 Gate now permits local evidence
and proposal staging only; it does not retroactively widen this overlay. No approved label,
held-label artifact, split or resolver result has been created.

## Verification

- Overlay creation and `--check` replay return `created` then `unchanged`; the prior proposal also
  replays unchanged.
- Nine overlay tests cover exact hash/ID scope, deterministic materialization, public privacy,
  widening rejection, private-authorization tamper, proposal-parent drift, core fail-closed behavior
  and dependency boundaries.
- Six readiness tests verify the post-overlay status, CLI/hash replay and premature/tampered inputs.
- All 128 representative-benchmark tests pass. Ruff, formatting, strict MyPy, compile, canonical
  JSON, file modes and Git-ignore checks pass.
