# T49.3 — Optional human-storage profile requirements

Date:2026-09-14. Lite. DRAFT; owner requirements/design/tasks confirmation pending.
This checkpoint delivers planning only, not a frozen approved protocol, adapter, SQL test or deployment.
Upstream:95be1fbe5c2d9d48aec80d471314bbfa47dcb2c2; T49.2 isolated correctness PASS.

## Goal and authority

Demonstrate a separately versioned PostgreSQL-backed **human knowledge storage** option while
keeping canonical resolution unchanged. PostgreSQL stores/validates the snapshot; human candidate
selection still uses in-memory identity-gated hashing/RRF. This is not per-query SQL vector retrieval
or exact-release validation. Human RAG remains debug-only. Actual future HTTP requests include
read-only snapshot integrity SQL/network work; that work must not be hidden in timing exclusions.

### HSP-R1 — Preserve default and scored sources
WHEN the experiment is configured, THE SYSTEM SHALL use a new explicit entrypoint/profile/artifact
without modifying frozen API/config/service/v4/identity/data/final artifacts or the T49.2 sources/report.
WHEN the original entrypoint is used, THE SYSTEM SHALL retain its existing behavior and defaults.
The105final-v2 questions SHALL NOT be loaded or queried by this experiment.

### HSP-R2 — Explicit immutable snapshot selection
WHEN a file-reference or PostgreSQL profile starts, THE SYSTEM SHALL require the original142doc
snapshot ID+content hash,12pinned sources, exact100provisional+42family types/payloads/origins and
unchanged exclusions; missing/mixed/partial/altered input SHALL fail closed with no latest/fallback.
The new test namespace SHALL NOT lift original canonical/ingestion exclusions or mint canonical IDs.

### HSP-R3 — Read-only application and live integrity gate
WHEN an experimental /health or /resolve request arrives, THE SYSTEM SHALL revalidate the complete
selected snapshot against the cached snapshot before using the cached index. File reference SHALL
check its pinned plan/source bytes; DB mode SHALL read the whole selected snapshot in a read-only,
repeatable-read transaction, with a SELECT-only database role. The application SHALL NOT migrate,
import/update/delete/repair snapshots. Bootstrap/review corruption tests belong only to a separately
authorized new disposable test DB. No existing DB/volume or production URL fallback SHALL be used.

### HSP-R4 — Failure readiness and no stale-success fallback
IF startup or request integrity validation fails, THEN /health SHALL return503/notready and valid
/resolve SHALL return503 without identity. Post-start DB disconnection/corruption/partial snapshot
SHALL be covered. Readiness SHALL latch failed until process restart; no background retry, automatic
snapshot switch or file fallback. Invalid HTTP requests SHALL retain the existing400/415/422 contract;
readiness probes SHALL not turn an invalid request into a false successful result.

### HSP-R5 — Frozen mathematics and exact parity
WHEN the new profiles retrieve human candidates, THE SYSTEM SHALL reuse unchanged v4 mathematics
at floor0.5/characterweight1/hash192/RRF60/source25/union≤50 and the existing identity admission/noise/
work limits. Onlycasting (plusapprovedfamilyaliases) SHALL govern human admission. The old math
protocol hash SHALL remain distinct from the new storage protocol/artifact hash. Candidate order,
types/IDs/payloads/all rank+score components and work counters SHALL match file-reference versusDB.
Human information SHALL NOT alter canonical UUID/product/status/confidence/policy/calibration.

### HSP-R6 — Development-only fixed comparison
WHEN parity is evaluated, THE SYSTEM SHALL use the pinned199development cases only, with no floor/
weight/source/threshold search or winner selection. All199cases, including controls/empty results,
SHALL be retained. Bothprofiles SHALL make199one-pass correctness calls each withoutprewarmups;
the unchangeddefault SHALL make199nondebug referencecalls. No retries/dropcases.
Canonical nondebug response bodies SHALL equal the original-default reference on those same cases.
Known development labels MAY supply diagnostics but SHALL NOT be new holdout/population accuracy.

### HSP-R7 — Output-before-score and source/version binding
BEFORE any real experimental retrieval or timed request, THE SYSTEM SHALL freeze approved specs,
new protocol/profile JSON, snapshot/source hashes, producer/adapter sources and runtime image IDs
at committed versions. It SHALL record legacy dev/final output exposure and new-output-not-yet-viewed
honestly, publish immutable raw199case outputs before parity scoring, and retain everyfailed run.
Private mocks before code freeze SHALL NOT be represented as real experimental results.

### HSP-R8 — Honest bounded cost protocol
WHEN cost is measured, THE SYSTEM SHALL follow the proposed protocol-draft after approval:5fresh
startup samples perprofile;199case paired HTTP samples after3warmups perprofile;199paired human-core
samples after3warmups perprofile, singleworker/concurrency1, perf_counter_ns/nearest-rank p95.
HTTP SHALL include completeintegrity revalidation/SQL/network/signalextraction/canonical+human
resolution/serialization+parsing; core SHALL exclude those separately disclosed costs. Errors and
abstentions SHALL be retained, with no timed reruns to pass budgets. Proposed ceilings:startup p95
5000ms, integrity p95150ms, HTTPp95250ms, human-corep9525ms; no production SLA/real3k/scale claim.

### HSP-R9 — Traceability and closure boundaries
WHEN this checkpoint is delivered, THE SYSTEM SHALL update tasks/QA/AIrubric/decision/narrative log
within the independent project directory and distinguish draft, approvedfreeze, implementation,
storedresults and runtimeclosure. T49.3planning SHALL NOT mark fullT49.3/T49.4 complete. Dataset
expansion, ANN/neuralembedding, wheel/tampo identity changes and defaultrollout remain separately gated.
