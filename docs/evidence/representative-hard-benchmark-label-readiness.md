# RHB-T6 label-authoring readiness evidence

Date: 2026-10-05
Mode: Lite / Lean Industrial
Verdict: **VALIDATOR PASS — OWNER GATE NOT REQUESTABLE**

## What was checked

The new read-only readiness validator answers whether the current 60-case RHB-T5 artifact may enter
owner labeling. It replays the private pack through both its deterministic materialization validator
and the core `validate_query_pack()` contract, revalidates T1/T3, verifies the 20-record CAR-T6
authority checksum/Gate, inspects only safe source-permission metadata, confirms that no label or
RHB-T6 authorization artifact exists, and publishes a hash-bound result.

It creates no label, held case, authorization, split or resolver result. It imports no FastAPI,
resolver, browser or network client and does not consult historical human labels or resolver output.

## Contract defect found and repaired

RHB-T5 truthfully attributed the 60 selections to
`fresh_output_blind_independent_agent`, but the older cross-artifact query validator accepted only
`project_owner`. The RHB-T5 builder had used `QueryPack.model_validate()` directly, so its focused
tests passed while the later `validate_labels()` path would reject every case when it revalidated
the pack.

The repair does not weaken authorship generally. The core validator now accepts the fixed
independent-agent role only when the pack is local-only and the source is the approved Human query
source. Historical `project_owner` authoring remains valid; arbitrary authors and misuse on public
or unrelated-source rows remain rejected. The RHB-T5 builder now calls the core query validator, so
schema validation can no longer bypass source, scope or author invariants.

## Readiness result

The 60-case pack is intact, label-free and core-valid, but three data/governance blockers prevent an
RHB-T6 Owner Gate:

1. **Matched-label permission is `0/20`.** Every query uses
   `human-labeled-real-noisy-v1`. Frozen T3 permits that source to produce only `ambiguous` and
   `no_match`, not `matched`.
2. **CAR authority is not admitted by frozen T1/T3.** The 20 CAR records use
   `fandom-hot-wheels-2025-pilot-r790665-v1`; the later CAR workflow accepted those records under its
   own owner-reviewed governance, while the older RHB source contract still classifies that source
   as `prohibited/staging_only` for exact authority.
3. **Provisional challenge shortfalls total `16`.** Year `3`, color `3`, series `4`, identifier `2`
   and unknown-to-catalog `4` remain unverified/short.

The deterministic report therefore returns:

```text
status: blocked_before_owner_gate
query pack: 60 rows; core validator passed; representative_pilot=false
matched label target / permitted: 20 / 0
CAR authority: 20 records; T1/T3 compatible=false
challenge shortfall total: 16
labels present: 0
RHB-T6 authorized: false
owner Gate requestable: false
readiness SHA-256: b4bf8f9a45b315a2ad64ba9f5626daef63a246c66bbbfc884856b7945e1b9f45
```

## Decision and next allowed action

The validator does not reinterpret the prior Owner Gates. CAR-T6 proved a later community-snapshot
authority bundle under the CAR workflow; it did not silently rewrite the frozen RHB T1/T3 source
decision. Likewise, authorizing RHB-T5 query selection did not authorize matched labels.

The next allowed action is to prepare a versioned source-decision and authority-admission repair for
owner review. That proposal must preserve the rule that Human query/labels cannot themselves create
a UUID: any future matched label would still need to bind one independently admitted CAR authority
record. No RHB-T6 Owner Gate should be presented until the repaired contracts pass readiness.

## Verification

- Six direct readiness tests pass: deterministic real state, CLI/hash replay, premature-label
  rejection, query-manifest tamper, authority tamper and dependency guard.
- All `118` representative-benchmark regressions pass after the author-role repair.
- Ruff/format, strict MyPy, compile and diff checks pass.
- The builder still reproduces the private query pack as `unchanged`; no query or label row is added
  to Git.

A full-repository run was sampled for approximately 2.5 minutes and showed no failure through the
displayed 5% checkpoint plus subsequent progress. It was manually stopped because unrelated slow
model/evaluation tests make that run disproportionate for Lite mode; this milestone therefore does
not claim a new full-suite PASS.
