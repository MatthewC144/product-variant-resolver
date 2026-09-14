# Identity-Bounded Retrieval — Lite IBR-T1 Checkpoint

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
