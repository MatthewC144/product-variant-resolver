# Identity-Bounded Retrieval — Lite IBR-T1–T5 Checkpoints

## Current IBR-T5 final family-quality and Lite closure — 2026-09-14

Verdict: PASS for this feature's scoped family retrieval and Lite engineering/runtime gates.
NOT production/release-variant accuracy, default deployment or ingestion approval. T49 DESIGN ONLY.

Bench87bbd19 precedes evaluatorb86578c, which precedes one105-query run. Separate integrity
preflight reads approved labels only to validate; collection/scoring process does not parse them
until105 raw ranks/work/errors are durably published. Zero final warmups/retries/configuration
changes. Raw/source/event-order/RRF/work checks reproduce JSON/Markdown without querying again.

| Requirement | Produced evidence | Result |
|---|---|---|
| R1–R2 | Oldv1/v3/dev byte replay and frozen protocol/winner chain | PASS |
| R3–R8,R11 | Prior posting/oracle/admission/budget tests plus final raw candidate/RRF/work replay | PASS |
| R9–R10,R12 | Complete frozen21-config T3 report, retained real/scale/subgroup samples and known-target gates | PASS |
| R13 | Genuine artifact/source loading, fresh non-root/read-only image, absent/malformed/stale503 | PASS |
| R14 | Host/API/unit checks plus actual default/v4 HTTP canonical equality and typed debug/UI | PASS |
| R15 | Owner approval105pairs, labels/code committed first,9 unchanged gates, all105 raw rows/4misses preserved | PASS |
| R16 | Full/regression/historical/cost/runtime/doc/AI gates; T49 design only | PASS |

Final positives80/84@5(95.24%),77/84@1(91.67%),MRR0.93254; marketplace42/42,lexical38/42;
family coverage42/42,merge4/4,forbidden0,unrelated0/10,retrieval errors0. Four lexical misses are
published unchanged; no closer-result tuning. Diagnostic p95=6.945209ms,105 in-process samples,
zero warmups, extraction excluded/serialization included; not a new cost gate or HTTP latency.
Inherited T3 real/scale p95=2.065375/45.138542ms remain source-valid, not remeasured.

32 new focused evaluator/closure tests and411 full tests PASS, no skips, one existing warning.
RuffF/I,isolated strict MyPy,compile,Node,Compose(default/postgres static only),old/v4 report replay
PASS. Docker Python3.12.14/Linuxaarch64/uid100/read-only loopback Uvicorn one worker smoke PASS.
Initial image v4ROOT mismatch503 was corrected only in DockerPYTHONPATH, not pinned runtime;
relocated-identical-artifact fixture falsely expected503 and was corrected to wrong mandatorySHA.
Both failures retained; final raw results never repeated or modified. No PostgreSQL writes/load test.
See [final/closure evidence](../../docs/evidence/family-retrieval-final-v2.md) and
[AI evaluation](../../docs/evidence/ai-evals/family-retrieval-final-v2.md).

## Historical IBR-T4 approval/label checkpoint — 2026-09-14

T4 engineering and family-target approval: PASS. Final model quality/runtime closure/T49:
NOT EVALUATED. Explicit owner target confirmation followed by scope explanation and consent to
proceed are recorded verbatim; generic next-step messages alone were not accepted as approval.

R15: all105 decisions bind committed query SHA/case hashes; positive42×2 target review-family IDs/
UUIDs, merge4 target provisional casting IDs/UUIDs with forbidden source IDs, held7 exclusions
(not a forced-empty condition), unrelated10 zero-result controls. No canonical/release variant
truth inferred. Query/winner/source bytes unchanged. All three approved documents are exclusively
published in a separate complete child directory; strict type-sensitive metadata/target/source
validation and commit-before-score checks are implemented without new-final retrieval.

28 new label tests /50 focused /379 full tests PASS, no skips, one existing warning. The initial
full invocation without PYTHONPATH failed one module-resolution subprocess test (378 pass); the
correct PYTHONPATH=src invocation passes all379 without product-code changes. Focused Ruff F/I,
isolated strict MyPy, compilation, correct Node UI syntax and historical protocol/v4/v1 replay PASS.
No fresh Docker runtime or final-v2 retrieval/scoring. See
[approval evidence](../../docs/evidence/family-retrieval-final-v2-label-freeze.md) and
[AI artifact assessment](../../docs/evidence/ai-evals/family-retrieval-final-v2-label-freeze.md).

Next: commit/verify approved benchmark, then T5 single final evaluation and runtime/full closure.
Defaultv2 and originalFAILs remain unchanged; real catalog expansion remains unauthorized.

## Historical IBR-T4 preparation checkpoint — 2026-09-14

Query preparation engineering: PASS. Owner approval/expected labels: PENDING; whole T4 incomplete.
Final model quality/closure/T49: NOT EVALUATED. STOP here, do not infer approval from proceed requests.

R15 partial: verified winner commit `a9a3730` ancestor/input bytes before query freeze; all105 new
query/reference pairs cover84/4/7/10,42 families×2styles; old/dev/indexed/compact/nonempty-core
reuse and no-v1-label/no-new-retrieval guards pass. Complete owner table/105 case hashes are delivered.
Query SHA `b23b69912c678c027461c96eb23f113484c5a8ed6218c06d90026704abe5102b` is awaiting approval.
Family coverage keeps42-group denominator; unapproved misnamed draft/source snapshots preserved,
same questions and no outputs. No expected labels/benchmark/approval/final score exists.

22 new focused /351 full tests pass, one old warning; lint/type/compile/static Compose/Node and
historical reproduction pass. No fresh image runtime; no source-bound runtime or catalog changes.
See [freeze evidence](../../docs/evidence/family-retrieval-final-v2-query-freeze.md) and
[AI artifact assessment](../../docs/evidence/ai-evals/family-retrieval-final-v2-query-freeze.md).
Next only after explicit owner confirmation: approval recording/attributable labels/benchmark commit,
then one final score and full closure. Defaultv2, originalFAILs and T49 remain unchanged.

## Historical IBR-T3 checkpoint — 2026-09-14

T3 G2/G3* engineering: PASS. Frozen development quality/safety/cost: PASS, all 21 configurations.
Entire feature/final/runtime closure: NOT EVALUATED. Selected 0.50/1.0 artifact is experimental only.

R9–R10: all 4,179 real outputs retained; selected positive 168/168, each style 42/42, merge 4/4,
forbidden 0, unrelated 0/20, MRR0.9911; fixed tie-break/denominators/safety/cost gates pass.
R11–R12: 2,520 raw scale outputs/work, 199/120 latency samples/config, original-20 subgroup,
known target 60/20/20 hits and cost 2.07/45.14 ms p95 pass. Numeric-core/wrapper-edit and initial
brief test-process overlap are disclosed, not rerun or generalized. R13–R14: genuine checksum-bound
artifact/API loading, source/raw metric replay, exclusive publication and canonical/default-v2 checks pass.
R1–R2: unchanged freeze/protected reports/sources and guarded no-v1 selection reads pass.

18 new tests / 48 focused T3+artifact / 329 full tests pass, one prior warning; focused lint/type,
compilation, historical checks, Node/static Compose/context pass. No fresh Docker image runtime.
See [T3 evidence](../../docs/evidence/human-knowledge-identity-development-v1.md) and
[AI evaluation](../../docs/evidence/ai-evals/human-knowledge-identity-development-v1.md).

R15 owner-reviewed new 105-question final lifecycle and one score remain T4/T5; R16 full runtime/
regression/quality closure and T49 remain gated. Next permitted work after committing qualified
winner/code/report/artifact is T4 output-blind authoring and owner approval, not scoring/ingestion.

## Historical IBR-T2 checkpoint — 2026-09-14

G2/G3* for IBR-T2 engineering: PASS. Entire feature/quality/cost approval: NOT EVALUATED.
T1's original record below remains historical. R3–R8/R11 arithmetic/admission/caps/ordering are
implemented and checked with independent cosine oracle and bounded failure tests. R13–R14 are
checked by strict evidence parser, API readiness/conflict/local-work/health/UI and unchanged
canonical response tests. R1–R2 remain checksum-valid without protected source/report edits.

65 focused tests / 311 full tests pass (one existing warning); focused lint/type checks, compilation,
Node syntax, historical reproduction and static Compose/context checks pass. No fresh Docker runtime
was executed. Artifact success fixtures mock selection validation; no real qualified winner exists.
See [T2 evidence](../../docs/evidence/human-knowledge-identity-implementation-v1.md) and
[AI assessment](../../docs/evidence/ai-evals/human-knowledge-identity-implementation-v1.md).

R9–R10/R12 real-grid metrics, 199/120 latency/correctness and full raw-report replay await T3.
R15 final lifecycle/score and R16 full closure await T4/T5. Default v2, historical FAILs, no new
final pack, no real ingestion and T49 blockade remain. Next permitted task is T3 under unchanged
protocol; no winner must STOP rather than advance to final authoring.

## Historical IBR-T1 checkpoint

Date: 2026-09-13. Scope: protocol/approval/static core and workload validation only.
G1* owner confirmation: PASS. IBR-T1 engineering: PASS. V4 model quality/cost: NOT EVALUATED.

The owner's proceed instruction confirms the three spec hashes at `880e4f5`; historical snapshots
and separate approval event remain checksum-bound. T1 outputs were generated before any v4 ranking.
It preserves the old pack/final/v3 evidence and freezes source hashes, noise/core/formula/limits,
21 settings, selection gates, all 199 real IDs and 120 scale query/target pairs. Byte checks and
non-overwriting invalid-input behavior pass. No protocol/rule change was informed by new output.

| Requirement | Current evidence | Status |
|---|---|---|
| R1–R2 | Frozen snapshots/approval/source references; guarded no-v1 reads/no retrieval; old report checks | T1 PASS |
| R3–R4 | Casting/alias-only static audit, ignored broad-label test, Unicode/numeric/whole-token tests | Static PASS; runtime deferred |
| R7 | Empty/short/excessive form/query/window rejection; work ceilings frozen | Static PASS; posting-abort behavior deferred |
| R9–R10 | Exact original grid/thresholds/denominators frozen | Contract PASS; execution deferred |
| R12 | 60/20/20/20 workload targets/gates and numeric-core limitation frozen | Construction PASS; timing/hit checks deferred |
| R5–R6,R8,R11,R13–R16 | Planned runtime/oracle/selection/final/closure artifacts not yet produced | NOT EVALUATED |

Full suite passes 248 tests with one pre-existing warning; focused 12 tests, Ruff F/I, isolated strict
MyPy builder check, compilation, old development/v3/v1 checks and whitespace checks pass. See
[protocol evidence](../../docs/evidence/human-knowledge-identity-protocol-v1.md).

Findings: two same-casting variant core collision groups are intentional; no cross-casting collision.
Synthetic casting cores reduce to digits and edited wrapper probes do not prove retained-core typo
quality. Preserve these limits of interpretation. Follow-up IBR-T2 must implement exact posting
scores/oracle, complete-core admission, all-or-nothing budgets and isolated runtime/debug failure
paths before selection. This is not whole-feature approval and T49 remains blocked.
