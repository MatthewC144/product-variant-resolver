# AI artifact rubric — T49.3 HSP-4 local cost

2026-09-15, Lite. PASS for the frozen142-document local cost protocol; production and3k NOT EVALUATED.

Grounding PASS:all5+5 startup,3+3 per-stage warmups and199+199 per-profile HTTP/core observations
come from the fixed development pack and pre-output v2 freeze. Authority PASS:the storage experiment
does not change canonical/human roles or retrieval parameters; human remains debug-only. Integrity
PASS:the scorer checks exact contract/counts,all statuses/errors,nearest-rank method and unchanged
ceilings before reporting eight passing p95 metrics. Safety PASS for isolated scope:internal network,
tmpfs database,read-only nonroot runner,SELECT-only reader,no host ports/production URL and exact
cleanup. Auditability PASS:raw-v2 SHA`78e9eb…7ed` precedes evaluation-v2 SHA`af5ff0…cccc`; every raw
duration/error/status/abstention is retained, and dependency-failed v1 remains visible. Cost PASS:
startup file/DB p95`271.142/300.175ms`, HTTP`38.645/46.163ms`, integrity`34.204/42.773ms`,core
`2.311/2.306ms`, all under pre-approved ceilings. Extendability BOUNDED:only local arm64,142 documents,
one worker and concurrency1 were measured.

Run-v1 produced no timing samples because`httpx` was absent from the fixed image. Switching to bundled
`urllib` preserved the runtime image and measurement boundary; a new committed freeze preceded v2.
No budget/retrieval tuning,timed retry,old final105 or real3k claim occurred. Focused79/full552 tests,
changed-file Ruff F/I,strict isolated MyPy and compileall PASS. One existing Starlette warning and54
unrelated whole-repo import-order findings remain disclosed.

This rubric closes bounded T49.3 only. It does not convert development timing into a production SLA,
storage validation into retrieval-quality evidence,casting knowledge into release identity,or142
documents into3,000 real products. T49.4/default rollout remains pending.
