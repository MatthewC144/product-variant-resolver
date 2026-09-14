# Identity-Bounded Human Knowledge Retrieval — Tasks

Mode: Lite. Status: IBR-T1/T2/T3 complete; IBR-T4 question freeze complete, WAIT for owner approval.
No subagents without explicit user request. All files under `Product Variant Resolver`.

## IBR-T1 — Freeze the owner-approved new execution protocol

- [x] Validate restricted identity cores/collisions/form limits and author the exact 120-query scale
  workload without viewing v4 output. _(→R2–R4,R7,R12)_
- [x] Freeze/commit protocol, policy, ceilings, same 21-config grid, source/development hashes and
  viewed-development reuse disclosure before any configuration execution. _(→R1–R2,R9)_

Files: `scripts/build_human_knowledge_identity_protocol.py`,
`data/evaluation/human-knowledge-identity-development-v1/`,
`tests/test_human_knowledge_identity_protocol.py`,
`docs/evidence/human-knowledge-identity-protocol-v1.md`.

Acceptance: deterministic checksum/count/target/limit validation, atomic invalid-input preservation,
no v4 results yet, unchanged old pack/report/source files. If actual cores exceed proposed limits or
normalize empty, stop and return to design before code/config output, not quietly drop them.

## IBR-T2 — Implement the isolated v4 identity-posting retriever

- [x] Build exact-core token/IDF and normalized form-weight postings with unknown-gram query norms,
  direct accumulation, deterministic fusion and all-or-nothing budgets. _(→R3–R8,R11)_
- [x] Wire separate strict v4 configuration, query-local debug/health/UI evidence, conflict/failure
  readiness and unchanged canonical authority. _(→R13–R14)_

Files: `src/product_variant_resolver/human_knowledge_identity.py`,
`human_knowledge_identity_artifact.py` (strict evidence/parser decomposition), `config.py`, `service.py`,
`schemas.py`, `api.py`, `ui/app.js`, unit/integration/API/UI tests, Docker context dependency copies.

Acceptance: mathematical oracle equality before capping, empty generic-core results, full identity/
typo cases, source-rank correctness, cap discard/no shared mutable counters, evidence/conflict 503,
default v2 and debug-off canonical equality. Do not edit source-bound v3/normalizer/hashing modules.

## IBR-T3 — Run the frozen development selection and cost gates

- [x] Execute exactly 21 configurations; publish all 4,179 raw outputs/metrics/work counts/rejections
  and 199-real/120-scale latency samples with subgroup disclosure. _(→R9–R12)_
- [x] Check scale exact/context/typo targets, all development safety/quality/cost gates and deterministic
  tie-break; freeze a complete new v4 artifact iff all pass, otherwise FAIL/stop. _(→R10,R12–R13)_

Files: `human_knowledge_identity_selection.py`, separate report/freezer scripts,
`reports/human-knowledge-identity-development-v1/`, conditional new v4 artifact,
evaluation tests, `docs/evidence/ai-evals/human-knowledge-identity-development-v1.md`.

Acceptance: no v1 final data reads, raw report recomputes, no denominator exclusions, old v3 before
report unchanged, no-winner cannot create/overwrite artifact. No policy/cap/grid changes after output.
Winner/code/protocol/report must be committed before T4. FAIL blocks T4–T5 and T49.

## IBR-T4 — Freeze and obtain approval of a new unseen final v2 pack

- [x] After winner/code commit, author/freeze 105 new output-blind questions with 84/4/7/10 coverage,
  reject reused original/dev/indexed queries and present every pair/checksum to owner. _(→R15)_
- [ ] Stop for explicit owner approval before labels or retrieval; then freeze attributable labels/
  benchmark against unchanged queries. _(→R15)_

Files: v2 final authoring/decision/builder scripts, `data/evaluation/family-retrieval-v2/`,
final lifecycle tests and review evidence. Supersedes unstarted HRR-T4/T5 implementation, not its gates.

Acceptance: history proves winner precedes authoring; all 105 pairs approved unchanged, no v4
candidates viewed during authoring/review, and labeled benchmark committed before scoring.

## IBR-T5 — Run one final score and close the Lite gate honestly

- [ ] Retrieve before final label access, publish all raw ranks/errors and unchanged final gates;
  preserve a final FAIL without tuning. _(→R15)_
- [ ] Run full tests/historical data checks/canonical and cost regressions, compilation/API/UI/
  packaging checks; update QA, AI-eval, README, decision and narrative Project Log. _(→R1,R11–R16)_
- [ ] Authorize T49 design only on complete final PASS; no actual ingestion/default deployment is
  implied by closure. _(→R16)_

Files: v2 evaluator/report tests, final reports, this feature's `review.md`, evidence and docs.
Acceptance: engineering/quality separated, all requirements mapped to produced evidence, stale/
missing runtime packaging fails 503, cost/safety never waived, original failures remain published.

## Dependency order and approval

Owner confirms requirements → design → tasks → T1 protocol freeze/commit → T2 code/oracle →
T3 selection/cost → qualified winner commit → T4 output-blind questions → owner approval/labels →
T5 one final score/closure. No winner branches to STOP/design, not T4.

G1* is confirmed by the owner's `執行下一步` response to the three-spec handoff. Approval of commit
`880e4f5` and exact spec hashes is recorded in the frozen `owner-approval.json`; original approved
spec snapshots retain their historical proposed headers. T1 passes with 142 nonempty document cores,
284 forms, two same-casting variant collision groups, zero cross-casting collisions, and 120 scale
queries. T2 implements v4 under isolated runtime configuration. T3 now publishes the complete
21-configuration development/scale report and selected artifact: floor 0.50, character weight 1.0.
All gates PASS; default remains v2, original reports/FAILs and protocol remain unchanged. See
`docs/evidence/human-knowledge-identity-development-v1.md`. Winner/code/report/artifact must be
committed before T4 authoring. T4 now freezes 105 query/reference pairs and a full owner-review
table, bound to winner commit `a9a3730`. See `data/evaluation/family-retrieval-v2/owner-review.md`.
Owner approval/labels and T5 scoring are NOT executed; stop here for explicit approval of the frozen
pairs/checksum. Engineering preparation is not whole T4 completion or final PASS. Family coverage
retains the inherited 42-family denominator; a pre-approval misnamed draft is preserved/superseded.
Independent-final/runtime-closure/T49 remain gated. Synthetic scale is not real catalog expansion.
