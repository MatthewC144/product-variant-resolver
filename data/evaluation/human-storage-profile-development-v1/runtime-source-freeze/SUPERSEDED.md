# Superseded HSP-2 source candidate

This uncommitted candidate was generated from commit `5d9e2f30e2ddf6384a15c24169e3e4c5bcbcff86`
after initial focused tests. It correctly declared runtime/SQL/output readiness false, but the
HSP-2 task review then found that the new `/health` wrapper did not publish the required separate
versioned `human_knowledge_storage` dependency. The candidate is retained rather than overwritten.

It is NOT the accepted HSP-2 source freeze and its old four-file exact-bundle check is intentionally
invalidated by this explanatory fifth file. No SQL, real199 retrieval or timed output used it.
The accepted successor is `../runtime-source-freeze-v2/`, generated only after the health contract,
tests, producer and all bound sources are committed together.
