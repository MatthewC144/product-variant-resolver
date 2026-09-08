# Product Variant Resolver — MVP Decisions

> Status: accepted for the Lite/MVP fixture path on 2026-09-01. Architect, security, and
> performance reviews were not run and remain deferred.

## D1 — Ship an offline fixture baseline first

- **Choice:** Make the version-controlled catalog and dependency-light in-memory pipeline the
  executable default.
- **Reason:** It provides a deterministic demonstration and a reproducible evaluation loop without
  network, database, paid API, or GPU dependencies.
- **Alternatives:** Real marketplace catalog ingestion; PostgreSQL/pgvector as the only runtime;
  hosted retrieval/model APIs.
- **Impact:** The checked-in metrics describe only 21 synthetic fixture test cases. They do not
  establish production accuracy, marketplace coverage, or production readiness.
- **Deferred review:** Real-data provenance/coverage and production catalog design.

## D2 — Keep product knowledge in catalog data

- **Choice:** Application code parses generic syntax; color, series, aliases, identifiers, and
  variants come from catalog data.
- **Reason:** A catalog-only change can add knowledge without another product-specific branch.
- **Alternatives:** Hard-coded series/color dictionaries or variant rules in the resolver.
- **Impact:** Structured matches and conflicts remain explainable. Conflicts are ranking features,
  not destructive filters.
- **Deferred review:** Governance and validation for externally sourced catalog changes.

## D3 — Use RRF as the default ranker

- **Choice:** Default to reciprocal-rank fusion. Keep `heuristic-v1` available only through
  `PVR_RERANKER_ENABLED=true` and for offline ablation.
- **Reason:** On the same 12 matched frozen-test cases, RRF and `heuristic-v1` each produced Top-1
  `1.0`; the absolute reranker gain was `0.0`.
- **Alternatives:** Always run the heuristic; add raw sparse/dense scores; use a pinned local
  cross-encoder.
- **Impact:** The default path avoids an unproven stage while retaining its interface and debug
  fields. This decision says nothing about external cross-encoders because none was evaluated.
- **Deferred review:** Revisit with real hard negatives and a pinned neural model.

## D4 — Calibrate and abstain

- **Choice:** Fit calibration on grouped train data, select thresholds on grouped dev data, and
  freeze the policy before evaluating test labels.
- **Reason:** A resolver must be able to return `ambiguous` or `no_match`, not force a nearby
  identity.
- **Alternatives:** Always choose Top-1; use a fixed uncalibrated score cutoff.
- **Impact:** The API has three lowercase decision states. Current test evidence shows precision
  `1.0`, false-match rate `0.0`, and coverage `0.8333`, but only on the synthetic fixture test.
- **Deferred review:** Larger calibration sets, uncertainty intervals, and a full
  precision–coverage frontier.

## D5 — Treat PostgreSQL and external models as deferred adapters

- **Choice:** Preserve Alembic schema, parameterized SQL constants, Compose profile, and provider
  interfaces, but fail readiness when an unavailable provider is selected.
- **Reason:** Static scaffolding exists, but there is no runtime evidence for PostgreSQL ingestion,
  FTS, pgvector retrieval, or pinned external embedding/reranker artifacts.
- **Alternatives:** Remove all adapter scaffolding; delay the repository until every external
  dependency is integrated.
- **Impact:** `PVR_BACKEND=offline`, `hashing-v1`, and RRF are the only verified defaults. The
  PostgreSQL profile reserves/migrates a future database path but does not switch API resolution.
- **Deferred review:** Migration cycle, database integration/E2E, model license/checksum, and
  external-model cache behavior in Docker.

## D6 — Measure and name each runtime boundary separately

- **Choice:** Report direct pipeline, warmed in-process FastAPI/TestClient, and host→Docker loopback
  latency as separate artifacts.
- **Reason:** This keeps the fixture CPU smoke reproducible and prevents it from being mislabeled as
  container or network performance.
- **Alternatives:** Publish one blended number; extrapolate loopback results to remote production;
  omit latency until load testing.
- **Impact:** The dedicated runtime artifact measures 50 sequential host→Docker loopback requests
  after 10 warm-ups at concurrency 1 and records nearest-rank p95 `4.721208 ms`. It includes Docker
  Desktop port forwarding but excludes startup, TLS, proxying, remote networking, concurrent load,
  and PostgreSQL. The fixture report's in-process ASGI p95 remains a different boundary.
- **Deferred review:** Formal performance review and TLS/proxy/remote/concurrency/PostgreSQL
  benchmark on representative infrastructure.

## D7 — Keep the reporter's HTTP client in runtime dependencies

- **Choice:** Declare `httpx2>=2,<3` as a runtime dependency rather than relying on the dev extra.
- **Reason:** The installed `pvr-report` CLI directly invokes FastAPI TestClient to collect its
  in-process HTTP samples, so the HTTP client is required in the shipped image rather than only in
  test environments. A no-cache rebuild with FastAPI 0.141.1, Starlette 1.6.0, httpx2 2.12.0, and
  httpcore2 2.12.0 generated and validated all six report artifacts in the read-only container.
- **Alternatives:** Move `pvr-report` to a separate reporting extra/image; replace TestClient with a
  standard-library or live-socket measurement; keep the dependency dev-only and make the installed
  CLI incomplete.
- **Impact:** The default runtime image is self-contained for API service and report generation,
  but carries an additional runtime dependency. Version ranges remain broad, and the dev extra's
  legacy `httpx` still emits a host warning.
- **Deferred review:** Add a lockfile or constraints file, reconcile `httpx` versus `httpx2`, and
  define a controlled dependency-update/rebuild policy.

## D8 — Keep reviewed real names separate until catalog alignment

- **Choice:** Import the 101 confirmed real-noisy-scan labels as a repository-owned auxiliary
  name-pair corpus, while excluding it from canonical-resolution accuracy, calibration training,
  and threshold selection.
- **Reason:** The source provides valuable initial-output versus human-verified-name evidence, but
  it does not yet provide a trustworthy mapping to this repository's immutable catalog UUIDs and
  slugs. Treating a matching text label as canonical ground truth would overstate what was verified
  and could leak evaluation labels into policy selection.
- **Alternatives:** Merge the records directly into `benchmark.json`; discard the 10 scans where
  recognition returned no candidate; copy the entire source workbook and image collection.
- **Impact:** The repository gains 91 directly comparable name pairs and 10 preserved recognition
  failures without changing the existing fixture-v1 headline metrics. The portable JSON excludes
  machine-specific frame paths and does not require the original workbook at runtime.
- **Deferred review:** Map reviewed labels to catalog identities, decide a casting-family grouped
  split, and only then promote an eligible subset into canonical resolver evaluation.

## D9 — Prefer explicit non-matches over fuzzy catalog assignments

- **Choice:** Align casting families only through exact normalized brand and casting names, and
  assign a canonical UUID only when exact series plus a variant discriminator leave one candidate.
  Fuzzy matching is disabled for ground-truth creation.
- **Reason:** The 120-item fixture catalog is synthetic and covers only 10 casting families, while
  the human corpus contains 97 real casting names. A high string-similarity score could make names
  such as `Dodge Challenger` appear close to `Dodge Charger` or collapse a chassis-specific Nissan
  Skyline into a generic family, creating false labels rather than measuring the resolver.
- **Alternatives:** Select the nearest text match for every row; manually force mappings based on
  domain intuition; create new canonical products automatically from incomplete name fields.
- **Impact:** The first alignment truthfully reports 0 canonical variants, 2 `Toyota Supra`
  casting-family-only records, and 99 unmapped records. This does not improve headline metrics, but
  it establishes exactly how much catalog work is required before real-data evaluation is valid.
- **Deferred review:** Define human-backed catalog provenance, deduplicate repeated scans, resolve
  uncertain series/variant semantics, and introduce a reviewable mapping workflow before expanding
  canonical ground truth.

## D10 — Separate casting identity from provisional variant identity

- **Choice:** Build a human-backed catalog with stable casting entities and nested provisional
  variants. Exact normalized brand/casting creates a casting; exact normalized series/variant
  groups source records into a draft variant. All draft variants require canonical review.
- **Reason:** The 101 confirmed labels reliably name castings, but do not consistently provide
  release year, collector number, color, scale, or edition as separate validated fields. Minting
  production canonical variants from those incomplete labels would make stable IDs depend on
  assumptions that may later be corrected.
- **Alternatives:** Create 101 unrelated products; merge everything by casting and discard variant
  differences; treat the free-text pricing keyword as a final natural key; wait until every field is
  manually re-labeled before retaining any catalog structure.
- **Impact:** All source evidence is usable for retrieval and review now: 101 cases become 97 casting
  entities and 100 provisional variant groups. One exact Chevelle structured duplicate merges while
  retaining both human names and case IDs. No provisional UUID is exposed as canonical truth.
- **Deferred review:** Add an explicit review queue for year, color, scale, series, edition, and
  collector number, then promote reviewed variants into a versioned canonical catalog.

## D11 — Run human knowledge as a non-canonical second RAG source

- **Choice:** Search the canonical fixture catalog and human-backed draft independently on every
  resolution. Canonical candidates continue through calibration and policy; human candidates use a
  separate sparse+dense RRF path and appear only as bounded debug/review evidence.
- **Reason:** The second corpus contains valuable verified names but provisional identities. Keeping
  the paths separate lets the system retrieve real casting knowledge without allowing incomplete
  records to generate a false canonical UUID or contaminate the existing calibration artifact.
- **Alternatives:** Merge provisional variants into the canonical catalog; run human retrieval only
  in an offline script; let the strongest human hit override `no_match`; omit the second source
  until every record is fully reviewed.
- **Impact:** A query such as `Hot Wheels BMW M3 GT2 Neon Speeders` retrieves the matching reviewed
  variant first while the API still returns `no_match` and null canonical identity. Debug output and
  the UI distinguish canonical candidates from human-review candidates; health fails closed if the
  required human catalog cannot load.
- **Deferred review:** Measure retrieval on a non-tautological held-out set, define promotion from
  provisional to canonical identity, and decide whether reviewed evidence may later influence—but
  never bypass—the calibrated decision policy.

## D12 — Treat PostgreSQL ingestion as an atomic full-snapshot installation

- **Choice:** Import one validated canonical catalog inside one database transaction. Reconcile
  product children without changing unchanged rows, reject identity/identifier collisions, and
  refuse an incoming snapshot that silently omits an already stored product.
- **Reason:** A partial commit would leave aliases, provenance, search documents, and catalog
  metadata describing different catalog states. Automatic deletion is also unsafe because a
  missing Wiki/export row may be a source error rather than an intentional product retirement.
- **Alternatives:** Commit each product independently; truncate and reload every table; use
  PostgreSQL conflict handling to reassign a Toy # to the latest product; automatically delete
  database products absent from the input file.
- **Impact:** First and repeated ingestion are identical, unchanged surrogate IDs/timestamps remain
  stable, and any collision or incomplete full snapshot rolls back before catalog metadata changes.
  Descriptive fields may be corrected under the same immutable UUID/slug. The trade-off is that a
  future removal needs an explicit active/retired lifecycle design rather than disappearing during
  import.
- **Deferred review:** Define staging/review/promotion for licensed external data, add product
  lifecycle state if retirement becomes necessary, and implement T09/T10 query adapters before
  selecting `PVR_BACKEND=postgres`.

## D13 — Introduce PostgreSQL through the sparse candidate boundary first

- **Choice:** When `PVR_BACKEND=postgres`, replace only the canonical sparse retriever with
  PostgreSQL built-in FTS. Keep dense and structured canonical sources in memory and keep the human
  catalog as an independent, non-canonical RAG source.
- **Reason:** T09 can prove database retrieval without coupling it to unfinished vector
  materialization. Retrieval remains a candidate-generation step; RRF, calibration, and abstention
  retain authority over the final result.
- **Alternatives:** Block all PostgreSQL API use until pgvector is complete; move all retrieval
  sources at once; let FTS Top-1 directly become the final identity; construct SQL or tsquery text
  by interpolating raw titles.
- **Impact:** PostgreSQL FTS uses a fixed parameterized statement, OR-combines normalized tokens for
  candidate recall, ranks with `ts_rank_cd`, and maps returned UUIDs back to the checksum-matched
  catalog. Startup refuses missing/stale metadata, and runtime database retrieval errors return 503.
  The accepted trade-off is a temporary hybrid backend and no PostgreSQL latency claim.
- **Deferred review:** Implement T10 vector materialization/exact pgvector retrieval, benchmark the
  database pipeline at approximately 3,000 catalog rows, and reconsider token/query weighting only
  from held-out retrieval evidence.

## D14 — Materialize the deterministic baseline before selecting a neural model

- **Choice:** Persist the existing 192-dimensional `hashing-v1` catalog vectors with a composite
  model/dimension/text-contract version, then execute exact cosine-distance search through pgvector
  when the PostgreSQL backend is selected.
- **Reason:** This closes and tests the durable vector lifecycle independently from model download,
  licensing, cache, and hardware decisions. The same adapter boundary can later accept a pinned
  neural embedding implementation without changing RRF or the API contract.
- **Alternatives:** Add a sentence-transformer and pgvector in one change; keep dense search in
  process; add an approximate HNSW/IVFFlat index at 120 rows; trust only a metadata row without
  checking per-product identity/version/checksum records.
- **Impact:** `pvr-materialize-embeddings` writes a complete artifact in one transaction and is
  idempotent for the same catalog. PostgreSQL startup regenerates expected checksums and refuses
  missing or stale rows. Exact `<=>` search avoids approximation variables at MVP scale. The cost is
  startup checksum work and a lexical hashing baseline whose scores are not neural semantics.
- **Deferred review:** Select a licensed pinned neural embedding artifact only with an independently
  written holdout evaluation. Measure exact-query latency at approximately 3,000 rows before adding
  an approximate index.

## D15 — Treat Wiki expansion as a revision-frozen review queue

- **Choice:** Start external catalog expansion with 100 text rows from one completed yearly list,
  fetched through the official MediaWiki API using an identified client. Freeze raw wikitext,
  revision/license metadata, normalized review records, checksums, and attribution. Do not insert
  these records into the canonical catalog or PostgreSQL product tables.
- **Reason:** The main risk at this stage is not query volume but silently converting community
  table rows into incorrect product identities. A small review queue makes table semantics,
  duplicate rules, missing fields, and license obligations inspectable before scaling to 3,000.
- **Alternatives:** Crawl individual casting pages and images; import all available years at once;
  infer colors from image filenames; assign canonical UUIDs automatically; wait for a separate
  hand-created CSV and build no reproducible source adapter.
- **Impact:** The importer makes two bounded API requests, checks the expected CC-BY-SA rights
  response, URL-encodes the page parameter, uses a 30-second timeout and 3 MB response limit, and
  downloads no media. The 2025 pilot contains 100 unique toy numbers and 45 explicit color-variant
  labels, but all 100 color fields remain null and all canonical UUIDs remain null. Source-derived
  data in its directory retains attribution and share-alike notice.
- **Deferred review:** Define human promotion rules for casting versus release identity, resolve
  missing color without image inference, and review the 100 pilot rows before fetching more years.
  A formal security/legal review is still required before unattended recurring synchronization.

## D16 — Match external candidates at family level before variant promotion

- **Choice:** Compare Wiki candidates with both catalogs using exact normalized brand plus casting
  only. Record all exact family candidates, but keep every row at `hold_for_human_review`; disable
  fuzzy matching, collector-number-only matching, and automatic UUID assignment.
- **Reason:** The staging table reliably names a casting but has no verified color, while repeated
  collector numbers and suffixes such as “2nd Color” describe releases rather than unique identity.
  Family-level comparison safely reduces manual work without pretending variant identity is known.
- **Alternatives:** Fuzzy-match similar names; use collector number as a global identifier; merge an
  exact human family automatically; classify every unmatched normalized name as a confirmed new
  casting; skip cross-source comparison and review all 100 rows from scratch.
- **Impact:** The 100 rows collapse to 53 family keys. Nine rows across four families point to an
  exact human-backed family, 91 rows across 49 families need possible-new-family review, and no row
  matches the synthetic canonical fixture. The report freezes candidate IDs and checksums but
  creates no database rows and changes no resolver output.
- **Deferred review:** A person must adjudicate the four existing-human-family groups first, then
  validate the 49 unmatched family names against reliable source context. Variant/color decisions
  and canonical UUID creation remain separate later steps.

## D17 — Make adjudication family-based, attributable, and promotion-ineligible by default

- **Choice:** Group the 100 row-level pre-reviews into 53 stable casting-family review items. Put
  exact existing-family candidates in priority 1, possible-new families in priority 2, expose only
  four permitted reviewer outcomes, and require actor/time/reason/evidence for completion.
- **Reason:** A reviewer should decide a casting relationship once rather than repeat it for every
  color or release row. At the same time, a machine suggestion must remain visibly different from
  a human decision, especially because the human-backed catalog is itself provisional.
- **Alternatives:** Ask for 100 independent decisions; mark exact matches merged automatically;
  allow free-form statuses; omit reviewer attribution; build a database admin UI before validating
  the decision contract; treat an AI-authored recommendation as human verification.
- **Impact:** The queue retains every source row exactly once, reduces the immediate workload to 53
  decisions, and provides a readable worksheet. All 53 decisions start pending and all families
  remain promotion-ineligible. The artifact can be regenerated without network or database access.
- **Deferred review:** The project owner or another named reviewer must adjudicate the four priority
  1 groups and then the 49 priority 2 groups. A later validator must reject incomplete or invalid
  completed decisions before any promotion artifact is generated.

## D18 — Separate family recommendations from variant verification

- **Choice:** For the four priority-1 groups, recommend an exact-name family merge while holding
  every release variant. Present Wiki rows, retained initial/human labels, series and variant
  fields, candidate IDs, and explicit token overlaps without filling reviewer-confirmation fields.
- **Reason:** Exact brand/casting names support a relationship between casting families, but they
  do not prove that releases from different years, series, or colors share a variant identity. The
  strongest overlap—Subaru BRZ with `zamac`—still has differing series labels and no verified color
  record from the Wiki table.
- **Alternatives:** Promote the four families automatically; merge both family and variants; show
  only normalized names and hide original evidence; require the reviewer to inspect raw JSON;
  refuse to make any recommendation despite exact cross-source family names.
- **Impact:** Four readable packets cover nine Wiki rows and four human provisional variants. Each
  proposes the existing human casting as a family target, preserves variant hold, and remains
  promotion-ineligible. No network, database, canonical catalog, or runtime behavior changes.
- **Deferred review:** The project owner must accept or reject the four family recommendations with
  attributable evidence. Variant identity requires a separate source-backed review even after a
  family merge is accepted.

## D19 — Preserve decisions as a separate, validated layer

- **Choice:** Store reviewer decisions in their own immutable input file and apply them to a derived
  adjudicated queue. Keep the original all-pending queue unchanged. For this batch, allow only
  exact-target family merges with `variant_decision=hold` and promotion eligibility false.
- **Reason:** Editing generated pre-review output in place would erase the distinction between
  machine organization and reviewer action, break deterministic regeneration, and make later audit
  or rollback difficult. A separate decision layer preserves who decided what and from which inputs.
- **Alternatives:** Edit queue JSON manually; regenerate the base queue with decisions embedded;
  treat follow-up authorization as variant approval; immediately update the human catalog or
  PostgreSQL; accept arbitrary target IDs; keep decisions only in chat history.
- **Impact:** Four family decisions are completed under `project_owner` provenance, 49 remain
  pending, nine Wiki releases remain variant-held, and zero families become promotion eligible.
  Invalid merge targets fail closed, and all inputs/outputs are checksum-frozen.
- **Deferred review:** Research and adjudicate the 49 priority-2 families. If variant promotion is
  later desired, introduce a separate source-backed variant decision schema and transactional
  importer rather than widening this family-only batch.
