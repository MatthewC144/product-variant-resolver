# RHB-T6 governance-repair proposal

Date: 2026-10-05
Mode: Lite / Lean Industrial
Verdict: **PROPOSAL PASS — AWAITING OWNER DECISION; NOT MATERIALIZED**

## Problem and selected repair

RHB-T6 readiness found two governance contracts that prevent useful labeling: the current Human
query source allows only `ambiguous/no_match`, while the later CAR authority bundle uses evidence
that frozen RHB T1/T3 still treats as staging-only. Editing the old decisions in place would erase
history; promoting all Human labels or the whole Wiki source would be materially broader than the
reviewed evidence.

The proposal therefore uses a checksum-bound overlay with two narrow admissions:

1. **Query-label admission:** only the current 60-row query pack may add `matched`, with a maximum of
   20. Every matched label must be owner-reviewed and bind an exact admitted authority ID/UUID.
   Human query/label evidence remains unable to create canonical identity.
2. **Authority-bundle admission:** only the exact 20-record CAR authority bundle is admitted. The
   evidence remains limited to Wiki revision `790665`; the entire Wiki source is not promoted, no
   manufacturer/global truth is claimed, and color/edition gain no new verification.

The proposal carries the provisional challenge shortfall total `16` into owner label review. It does
not preapprove representative-pilot status; owner review must verify a challenge or hold the case.

## Frozen bindings

| Parent | SHA-256 / value |
|---|---|
| RHB-T6 readiness | `b4bf8f9a45b315a2ad64ba9f5626daef63a246c66bbbfc884856b7945e1b9f45` |
| Private query pack | `97f7f0dd61cf619bb16b198778356d8ef53c7a504086f11542922f90706a858a` |
| CAR authority bundle | `72c11aeb8db03267a8deca4f50eb09d89c2c423a7e9ca983f498f76e80553117` |
| Proposal content hash | `e5d1d74233626dc715f253608d3ea05da8965b043e324255306523b3dffdf8de` |
| Proposal file hash | `0df96c2a37c133584b0c15e11b0f84c304b21c233739bc92031ffff56ef3d28a` |
| Query rows / authority records | `60 / 20` |

The proposal additionally binds raw checksums for the frozen source inventory, source decisions,
query-pack manifest and CAR re-audit manifest. Input paths are unique and sorted; authority IDs are
unique and sorted. Replay returns `unchanged`.

## Explicitly not authorized

- No frozen T1/T3 file may be modified in place.
- Human labels do not become canonical authority.
- The entire Wiki source does not become globally exact authority.
- The governance overlay may not be materialized before owner approval.
- RHB-T6 label authoring, RHB-T7 split and resolver evaluation remain unauthorized.
- The proposal does not claim Mattel/manufacturer or global Hot Wheels truth.

## Owner Gate draft

If the scope is acceptable, the next decision can use the following exact statement:

> 我批准 RHB-T6 Governance Repair v1：僅將 `human-labeled-real-noisy-v1` 的 matched-label
> permission 限定於 query pack SHA-256
> `97f7f0dd61cf619bb16b198778356d8ef53c7a504086f11542922f90706a858a`，且每筆 matched label
> 必須由 project owner 審閱並綁定 CAR authority bundle SHA-256
> `72c11aeb8db03267a8deca4f50eb09d89c2c423a7e9ca983f498f76e80553117` 內的 authority ID 與
> canonical UUID。我僅批准接納該 20-record bundle，不升格 Human labels 或整個 Wiki source
> 為 canonical authority，不代表 manufacturer/global truth，color 與 edition 不新增驗證。
> 此批准只授權 materialize versioned governance overlay，不授權 RHB-T6 label authoring、
> RHB-T7 或 resolver evaluation。

Approval of that text would authorize only the implementation and materialization of the overlay.
After the repaired readiness passes, RHB-T6 label authoring still requires another Owner Gate.

## Verification

- Proposal builder creates then reproduces `unchanged`.
- Eight focused tests cover deterministic scope, canonical materialization, real-file replay,
  authorization/widening rejection, public-field privacy, parent drift, proposal tamper and dependency
  guard.
- All 126 representative-benchmark regression tests pass; Ruff, format, strict MyPy, compile and
  diff checks pass.
- Public proposal contains no raw query, source-row reference, owner response, expected outcome/UUID
  or label record.
