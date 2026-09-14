# T49.3 planning review

Date:2026-09-14. Lite. Draft completeness/grounding PASS; G1* owner confirmation WAIT.
Requirements now CONFIRMED at the exact source recorded in [approval ledger](approval.md);
design and tasks/budgets remain WAIT. Requirements confirmation is not implementation approval.
HSP1–4 implementation/freeze/SQL/profilecost:NOT RUN. FullT49.3/T49.4 remain unchecked.

| Requirement | Draft acceptance path |
|---|---|
| R1/R9 immutability/scope | Newentrypoint/modules only; oldsource/final/default unchanged; statuses/log/rubric distinct |
| R2 complete142snapshot | ExactID/hash/12source pins/types/payloads/origins; no latest/fallback/sourceexclusion rewrite |
| R3/R4 readonly/failclosed | SELECT-only role, fullrequestsnapshot probe, startup/poststart503/latch, existinginvalidHTTP contract |
| R5 math/authority parity | Frozen0.5/1.0/hash192/RRF60/admission/limits, separate math/storageprotocols, canonicalbody unchanged |
| R6/R7 dev/freeze |199dev eachprofile+199defaultreference, no tuning/final105, committedsources beforeoutputs, raw before score |
| R8 cost |5startup/profile;3warmups/profile;199pairedHTTP/core; rawerrors/nearest-rank; proposedceilings needingapproval |

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
Owner confirms requirements first under spec-dev-loopLite; design/tasks/budgets then approval freeze.
