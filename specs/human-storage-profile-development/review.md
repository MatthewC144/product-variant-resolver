# T49.3 planning review

Date:2026-09-14. Lite. Draft completeness/grounding PASS; scoped G1 PASS after three sequential
confirmations at exact sources in [approval ledger](approval.md). HSP-1 input-freeze QA PASS:
8immutable-publication files,26input hashes, committed producer,16new/489full tests PASS,
Ruff F/I and strict isolated MyPy PASS. See [evidence](../../docs/evidence/t49-3-input-freeze.md).
HSP-2 adapter/mock/source-freeze PASS; see current findings below. HSP3–4 SQL/profilecost NOT RUN.
FullT49.3/T49.4 remain unchecked; no new SQL-run approval.

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

## HSP-2 QA addendum

Verdict:PASS for implementation plus private file/fake-DB/API tests and source freeze; no real SQL.
New modules only:`human_knowledge_storage_profile.py` validates strict/no-duplicate profile JSON,
all source/protocol/math/snapshot hashes, explicitly selected file/DB mode and runtime/mock state;
hydrates complete142typed documents once and re-reads the complete source for every probe.
`human_knowledge_storage_app.py` composes the existing factory/service. It probes only after a valid
resolve passes existing validation, adds debug-only storage timing/version, wraps health with a
versioned `human_knowledge_storage` dependency, and latches app service unavailable after a failure.
Original api/service/config/v4/snapshot/persistence/migrations/data/default files remain unchanged.

Coverage:R1/R5 original default +4 nondebug sample bodies byte-equal and old math artifact retained;
R2 exact142/100/42 and plan/source hashes;R3 file/fakeDB startup+each probe full read, explicit DB env;
R4 startup/runtime failure, health+resolve503/latch/no retry,400/415/422 no probes;R7 private mock
not-runtime-ready plus committed42-source candidate2. R3 SELECT-role SQL permissions and actual DB
transactions, R5 exact199 parity, all runtime failure fixtures and R8 costs belong to HSP3–4.

Focused55 and full544 tests PASS; Ruff F/I, strict isolated MyPy and compileall PASS. Initial test
iteration retained:reserved pytest parameter blocked collection; then37PASS/1FAIL exposed an invalid
test assumption that short`Chevy Nomad` must match (changed to the catalog-specific year/# case,
not production logic); first source-freeze tests50PASS/4FAIL exposed missing commit-wide byte checks,
which were implemented before publication. Candidate1 at5d9e2f3 lacked the required health field and
is retained/superseded; accepted candidate2 manifestSHA`ebd0fe…` binds42sources at`bd2a838` and
ready=false. Existing Starlette warning remains. Next:HSP-3 needs explicit isolated SQL-run approval.
