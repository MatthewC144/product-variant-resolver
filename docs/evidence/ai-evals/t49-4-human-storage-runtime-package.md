# AI artifact rubric — T49.4 optional runtime package

2026-09-15,Lite. PASS for bounded file-backed local packaging; production/PostgreSQL/3k NOT EVALUATED.

Grounding PASS:the runtime profile binds the exact corrected image,implementation commit,frozen142
snapshot,source manifest and math protocol. Four response comparisons and health/debug facts come from
the retained isolated Docker report,not from static Compose inspection. Authority PASS:the old package
hashes and default command are unchanged; human candidates remain debug-only and cannot replace the
canonical answer or UUID. Integrity PASS:missing profile is rejected,strict recursive source loading
succeeds inside v2,and the profile/report/package SHAs are fixed. The retained v1 failure shows the
recursive verifier caught a missing transitive input instead of silently starting.

Safety PASS for local scope:nonroot user,read-only root,read-only profile bind,tmpfs,loopback ports,
one worker,no database URL/credential/volume,and cleanup of exactly the labeled Compose project.
Auditability PASS:v1 and v2 reports are retained; implementation was committed before the exclusive v2
freeze,and v2 was frozen before runtime output. Full559/focused71 tests and the exact QA boundaries are
recorded,including one mistaken Ruff file selection and the pre-existing deprecation warning.
Extendability BOUNDED:explicit allowlisting makes dependencies reviewable but requires a newly versioned
package when recursive evidence changes. Only ARM64,file mode,142 documents and sequential smoke were
tested.

The raw runtime report SHA is`bac44242…761c`; image ID is`d8ccf54d…0e718`; package/profile SHAs are
`b89dfbc…624`/`a51d3112…980a`. This rubric must not be used to claim retrieval-quality improvement,
PostgreSQL rollout,concurrent throughput,production readiness,3,000 real products,source permission,
or color/wheel/tampo release identity.
