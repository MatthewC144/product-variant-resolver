# T49.3 bounded implementation review

Date:2026-09-15. Lite. Draft completeness/grounding PASS; scoped G1 PASS after three sequential
confirmations at exact sources in [approval ledger](approval.md). HSP-1 input-freeze QA PASS:
8immutable-publication files,26input hashes, committed producer,16new/489full tests PASS,
Ruff F/I and strict isolated MyPy PASS. See [evidence](../../docs/evidence/t49-3-input-freeze.md).
HSP-2 adapter/mock/source-freeze PASS; see current findings below. HSP-3 isolated SQL correctness
PASS after explicit owner continuation. HSP-4 frozen local cost protocol PASS; therefore bounded
T49.3 is complete. T49.4 packaging/default-rollout closure remains separate and unchecked.

| Requirement | Draft acceptance path |
|---|---|
| R1/R9 immutability/scope | Newentrypoint/modules only; oldsource/final/default unchanged; statuses/log/rubric distinct |
| R2 complete142snapshot | ExactID/hash/12source pins/types/payloads/origins; no latest/fallback/sourceexclusion rewrite |
| R3/R4 readonly/failclosed | SELECT-only role, fullrequestsnapshot probe, startup/poststart503/latch, existinginvalidHTTP contract |
| R5 math/authority parity | Frozen0.5/1.0/hash192/RRF60/admission/limits, separate math/storageprotocols, canonicalbody unchanged |
| R6/R7 dev/freeze |199dev eachprofile+199defaultreference, no tuning/final105, committedsources beforeoutputs, raw before score |
| R8 cost |5startup/profile;3warmups/profile;199pairedHTTP/core; rawerrors/nearest-rank; all eight local p95 gates PASS |

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

## HSP-3 SQL correctness addendum

Verdict:PASS for the fixed199 correctness/failure scope, not cost or deployment. Run-v4 binds
implementation commit`a9aa120`, exact file/DB profiles, fixed dev pack/protocol and two image IDs
before outputs. Its raw report SHA`193015…` was published and all owned containers/network removed
before the independent scorer created evaluation SHA`a6fdcb…`. File and PostgreSQL candidate ranks,
scores, discriminated types, UUIDs, payloads, v4 metadata and work counters match199/199; both
canonical projections equal the original nondebug API. All per-case health checks are200 and all
request IDs match. The21zero-candidate rows are retained.

The actual reader is LOGIN+SELECT on only`hk_snapshot`/`hk_document`, with super/inherit/create-role/
create-db false; INSERT/UPDATE/DELETE/TRUNCATE each returned42501. Ten startup faults returned
health/resolve503. Four post-start faults returned503 and remained503 after privileged restoration,
proving process-lifetime latch/no retry. Five invalid HTTP cases kept400/415/422 and zero probes.
Canonical seven-table digest stayed`1d7b7f…`; no production URL, host port, volume or oldfinal was used.

Runs v1–v3 are retained as unscored infrastructure evidence:DDL password bind syntax, FK-safe missing
snapshot deletion order and namespace CHECK constraint fault injection respectively. Each stopped,
cleaned only its exact owned resources and led to a new committed source/run freeze rather than
overwriting evidence. The first raw error echoed an expired generated credential; it was deliberately
not retained and a transparent sanitized failure record replaces it. Full suite548PASS plus focused59,
Ruff F/I, strict isolated MyPy and compileall PASS; one existing Starlette/AnyIO warning remains.
At the HSP-3 checkpoint,HSP-4 still had to measure startup/HTTP/core cost. The addendum below records
that later execution and supersedes this carry item without rewriting the historical HSP-3 evidence.

## HSP-4 local cost addendum

Verdict:PASS for the approved local142-document,concurrency1 cost scope. Run-v2 binds implementation
commit`31a97e4`, exact profiles/protocol/development pack and two image IDs before output. Raw SHA
`78e9eb…7ed` was published and the two containers/internal network were removed before independent
scoring produced evaluation SHA`af5ff0…cccc`. There were5 fresh startup samples/profile,3 HTTP and
3 core warmups/profile, then199 HTTP and199 core samples/profile in alternating order. All HTTP/core
samples succeeded; raw durations,status/errors/abstentions and environment are retained.

Nearest-rank p95 file/PostgreSQL results respectively:startup271.142/300.175ms under5000ms;
full loopback Uvicorn HTTP38.645/46.163ms under250ms; complete-snapshot integrity34.204/42.773ms
under150ms; initialized human core2.311/2.306ms under25ms. The PostgreSQL reader stayed SELECT-only
and cleanup had no errors or remaining owned resources. Runtime was Linux arm64,Python3.12.14,
PostgreSQL16.14,Uvicorn0.52.4,SQLAlchemy2.0.52,Alembic1.20.0 and psycopg3.3.5,UID100.

Run-v1 stopped before timing because the frozen runner image did not include`httpx`; its sanitized raw
failure and complete cleanup remain committed. The collector changed to Python stdlib`urllib`, which
preserved the frozen image and measurement semantics, and the supervisor now records hashed malformed
output failures. This correction was committed before a distinct v2 freeze; no budget or retrieval
setting changed and no timed retry occurred. Focused79 and corrected-environment full552 tests PASS;
the first full invocation without`PYTHONPATH=src` reproduced the known subprocess import failure.
Changed-file Ruff F/I,strict isolated MyPy and compileall PASS; the existing Starlette warning remains.

This closes only T49.3's bounded optional-storage experiment. It does not prove3k scaling,throughput,
durability,multi-worker behavior,production SLA,default rollout or color/wheel/tampo release identity.
Those remain T49.4/later work.
