# T49.3 planning review

Date:2026-09-14. Lite. Draft completeness/grounding PASS; scoped G1 PASS after three sequential
confirmations at exact sources in [approval ledger](approval.md). HSP-1 input-freeze QA PASS:
8immutable-publication files,26input hashes, committed producer,16new/489full tests PASS,
Ruff F/I and strict isolated MyPy PASS. See [evidence](../../docs/evidence/t49-3-input-freeze.md).
HSP2–4 adapter/SQL/profilecost NOT RUN. FullT49.3/T49.4 remain unchecked; no new SQL-run approval.

| Requirement | Draft acceptance path |
|---|---|
| R1/R9 immutability/scope | Newentrypoint/modules only; oldsource/final/default unchanged; statuses/log/rubric distinct |
| R2 complete142snapshot | ExactID/hash/12source pins/types/payloads/origins; no latest/fallback/sourceexclusion rewrite |
| R3/R4 readonly/failclosed | SELECT-only role, fullrequestsnapshot probe, startup/poststart503/latch, existinginvalidHTTP contract |
| R5 math/authority parity | Frozen0.5/1.0/hash192/RRF60/admission/limits, separate math/storageprotocols, canonicalbody unchanged |
| R6/R7 dev/freeze |199dev eachprofile+199defaultreference, no tuning/final105, committedsources beforeoutputs, raw before score |
| R8 cost |5startup/profile;3warmups/profile;199pairedHTTP/core; rawerrors/nearest-rank; owner-approved ceilings, measurement pending |

Inspection confirms APIalready supports `service_factory` and ResolverService accepts explicit
human catalog/v4config, so compositional newfactory is feasible without editing frozen sources.
HumanKnowledgeV4Config enforces the old mathprotocol hash; storageprotocol must be a separate
wrapper reference, not silently substituted. Currentrepository remains142/disposable-name bound.
Startup-only hydration does not detect later DBoutage/corruption; fullrequestintegrity gate is a
proposed explicit choice, with SQL/network costincluded inHTTP and failurelatchuntilrestart.
HTTPtitle500schema versus directcore512limits are distinct; no accidental APIexpansion proposed.

Actual current checks:JSONparse/draft flags/sourcehash references and document whitespace PASS;
storedT49.2report/localplan/finalintegrity checks PASS without newSQL/retrieval. Existing473testPASS
is upstream evidence, not a newly executed profiletest. No profiledata/results/authrole/DB/metrics yet.
The paragraph above records original planning checks, not the subsequent freeze results. HSP-1
now binds approved original spec bytes and derived storage protocol/declared profile separately
from the old math protocol. New protocol remains explicitly not runtime-ready: adapter/import
manifest and images are null; no real dev or timed outputs exist. First full-suite invocation
without PYTHONPATH had1failure/488passes due to subprocess import environment; corrected
`PYTHONPATH=src` invocation passed489. No old code/assertions or budget were changed to pass.
Carry: HSP-2 new adapter/app and runtime-source freeze; HSP-3 separately authorized SQL environment;
HSP-4 actual costs; existing Starlette/AnyIO deprecation remains. Publication is exclusive, not
OS-enforced immutability or crash-atomicity; partial bundles fail checks and cannot be overwritten.
