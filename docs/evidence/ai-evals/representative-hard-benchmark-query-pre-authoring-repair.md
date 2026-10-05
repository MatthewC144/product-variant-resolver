# AI artifact evaluation — RHB-T5 pre-authoring repair

Date: 2026-10-04
Scope: query projection, public manifest, split-contract repair and readiness v2
Verdict: **PASS — LEAKAGE CONTROLS EXECUTABLE, OWNER GATE PRESERVED**

| Rubric | Result | Evidence |
|---|---|---|
| Output blindness | PASS | Private rows contain only opaque reference and query; adjacent output/label fields are schema-rejected. |
| Publication | PASS | Raw rows are ignored/private; Git contains aggregate metadata and one irreversible hash only. |
| Split leakage | PASS | Query authoring has no split field; RHB-T7 owns the separate group-safe assignment. |
| Determinism | PASS | Projection creation/check is byte-stable and readiness v2 is hash-bound. |
| Tamper resistance | PASS | Source drift, unknown fields, missing ignore rule, partial outputs and atomic second-write failure fail closed. |
| Authority | PASS | CAR-T6 remains 20/7/0 while `rhb_t5_authorized=false` is unchanged. |
| Side effects | PASS | No resolver, browser, network client, query pack or label is used or created. |
| Claim calibration | PASS | `ready_for_separate_owner_authorization` is not described as dataset or model-quality completion. |

This evaluation fails if a future author can access the mixed source, if query text enters the public
manifest, if `split` reappears in T5 rows, if a generic continuation is accepted as authorization, or
if the projection's 91 available rows are described as an owner-approved 60-case benchmark.

Verification evidence: all 99 representative-benchmark tests pass; strict MyPy reports zero issues
across four benchmark modules; Ruff/format/diff checks pass; projection replay is
`unchanged / unchanged`; readiness v2 is
byte-identical across two runs; Git tracking checks prove the row-level projection is ignored; and a
fresh-clone-shaped public-manifest-only state rebuilds the private projection without changing the
tracked manifest.
