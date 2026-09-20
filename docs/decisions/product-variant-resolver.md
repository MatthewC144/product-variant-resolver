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

## D20 — Require two-source family evidence and hold disambiguated names

- **Choice:** Research priority-2 work in deterministic batches of ten. Recommend
  `create_new_casting` only when the queued name has one dedicated Hot Wheels Wiki casting page and
  at least one publisher outside Fandom confirms the exact Hot Wheels casting name. A
  disambiguation page forces `hold`, and every release variant remains held regardless of the
  family recommendation.
- **Reason:** “No exact family in our small catalog” proves only a coverage gap. The second-source
  rule reduces the risk of creating aliases as new families, while explicit disambiguation catches
  names such as `'55 Chevy` that refer to multiple physical casting tools.
- **Alternatives:** Treat every unmatched normalized name as new; rely only on the yearly Wiki
  table; demand manufacturer-only evidence for every historical model; research all 49 in one
  unreviewable change; or use image resemblance to choose a casting lineage.
- **Impact:** Batch 01 covers ten families and nineteen staged rows. Nine receive source-backed
  machine creation recommendations; `'55 Chevy` stays held because its 1982, 1998, and 2006 tools
  cannot be distinguished from the staged family name. The research is checksum-frozen and
  reproducible from its repository notes, but it does not complete a reviewer decision or mutate
  any catalog/database.
- **Deferred review:** The project owner must accept or reject the nine proposed family creations
  and keep/resolve the `'55 Chevy` hold. After attributable application, research batch 02 can take
  the next ten pending families. Release/color identity requires a separate evidence contract.

## D21 — Apply owner approval as a cumulative decision layer, not a catalog write

- **Choice:** Store the owner's T35 response as a separate ten-item decision batch and apply it to
  the T34 adjudicated queue. Require every research packet exactly once, require the approved
  outcome to match its frozen recommendation, retain family-only scope and variant hold, and emit a
  new cumulative queue rather than editing either earlier queue artifact.
- **Reason:** The user's short “execute the next step” follows an explicit nine-create/one-hold
  proposal, so it can be recorded truthfully as approval of that bounded set. It cannot be expanded
  into approval of release identities, canonical UUIDs, PostgreSQL insertion, or the other 39
  priority-2 families.
- **Alternatives:** Modify the T34 queue in place; immediately append entities to the human or
  canonical catalog; accept only the nine creations and omit the hold; allow partial batches; or
  rerun research with reviewer fields filled by code.
- **Impact:** Four prior merges plus ten new decisions yield fourteen completed and thirty-nine
  pending families. Nine are accepted as new review-layer casting-family decisions, one remains a
  family hold, and all twenty-eight release rows under completed decisions remain variant-held.
  Both decision batches and every input/output checksum remain auditable.
- **Deferred review:** Batch 02 should research the next ten pending families from the T36 queue.
  A later, separate catalog materialization design must decide how accepted review families receive
  stable entity IDs without becoming canonical variants prematurely.

## D22 — Continue research from cumulative state and treat homonyms as an identity conflict

- **Choice:** Build priority-2 batch 02 from the checksum-verified T36 cumulative queue, not the
  original all-pending queue. Continue to require a dedicated Wiki page and non-Fandom exact-name
  evidence for creation recommendations, but classify an exact display name shared by a separate
  historical casting tool as `homonymous_castings` and force `hold`.
- **Reason:** Once batch 01 has owner decisions, selecting again from the original queue would
  duplicate completed work. Exact spelling also does not guarantee one physical family: the
  current Batman and Robin Batmobile mainline and the separate 2004 100% Hot Wheels casting share
  a display name. A tool-unique identity is required before either lineage can safely become a new
  family entity.
- **Alternatives:** Reuse the original queue and manually skip names; treat every dedicated current
  page as sufficient even when another tool has the same name; merge both Batman tools into one
  family; or require manufacturer-only evidence for every historical casting. The first three lose
  determinism or identity precision, while the last would stop useful bounded research where
  reliable independent collector records are the available corroboration.
- **Impact:** Batch 02 covers the next ten pending families and eighteen staged release rows. Nine
  receive machine `create_new_casting` recommendations; Batman and Robin Batmobile remains held.
  The builder now supports batches 01 and 02 from one validated implementation, and both frozen
  outputs reproduce byte for byte. Reviewer fields remain pending, variants remain held, and no
  catalog, PostgreSQL, runtime, calibration, or evaluation artifact is promoted.
- **Deferred review:** The project owner must accept or reject these ten recommendations in a
  separate decision batch. Resolving the Batman hold requires a tool-specific mapping for HYW60
  and HYX61. After owner adjudication, batch 03 should select the next ten pending families from
  the newly derived cumulative queue.

## D23 — Append batch-02 approval to the decision history without materializing catalog data

- **Choice:** Interpret the owner's “execute the next step” response against the immediately
  preceding T37 proposal: accept the nine `create_new_casting` recommendations, retain the Batman
  hold, and keep all eighteen release rows variant-held. Store that authority in a separate
  batch-02 decision file and append it to the existing two-entry decision history in a new
  cumulative queue artifact.
- **Reason:** The prior message named the exact ten-family outcome and said owner confirmation was
  the required next step, so the follow-up provides bounded authorization. Replacing the history
  or writing directly to the human/canonical catalog would erase provenance and broaden a
  family-level approval into an unrequested identity or persistence decision.
- **Alternatives:** Overwrite the batch-01 queue; store only the latest batch in history; accept the
  nine creations but omit the hold; materialize eighteen searchable families/variants immediately;
  or leave authorization only in conversation history. Each alternative loses cumulative audit
  state, complete batch coverage, or the family-versus-variant boundary.
- **Impact:** The cumulative queue now contains twenty-four completed decisions and twenty-nine
  pending families: four existing-family merges, eighteen accepted new-family decisions, and two
  holds. All three owner-decision events remain ordered and checksum-bound. Forty-six release rows
  under completed family decisions remain held and promotion eligibility remains zero.
- **Deferred review:** T39 should research the next ten pending priority-2 families from the T38
  cumulative queue. A separate later design must assign stable review-catalog entity IDs to
  accepted families without inventing colors, releases, or canonical UUIDs.

## D24 — Distinguish differently named predecessors from same-name homonyms

- **Choice:** Build priority-2 batch 03 from the checksum-verified T38 cumulative queue and preserve
  the existing two-source creation rule. When a dedicated current casting has a related but
  differently named predecessor, retain that relationship as evidence but classify the exact
  queued name as `single_casting`; continue to hold cases where separate tools share the same
  display name.
- **Reason:** The newer `Hirohata Merc` is documented as related to the earlier, differently named
  `'51 Merc`, while `Fiat 500e` has its own dedicated identity apart from `Fiat 500`. Treating any
  related page as a homonym would create false holds. Ignoring related pages would lose the lineage
  distinction needed to prevent future accidental merging. The identity question is whether the
  exact queued name uniquely selects one tool, not whether any related casting exists.
- **Alternatives:** Automatically hold every family with a related page; merge predecessor and
  current tools; omit the relation because the names differ; or accept exact Wiki naming without
  independent corroboration. These options respectively over-block review, collapse physical
  tools, discard useful audit context, or weaken the established evidence rule.
- **Impact:** Batch 03 covers ten families and eighteen staged releases. All ten have a dedicated
  exact-name Wiki page plus at least one non-Fandom confirmation and therefore receive machine
  `create_new_casting` recommendations. Related Fiat and Mercury pages remain explicit evidence.
  Reviewer confirmation is still pending, every release variant is held, and promotion remains
  zero.
- **Deferred review:** T40 should present the exact frozen batch-03 packet to the project owner and
  record any approved family-only decisions separately. Stable catalog materialization and variant
  verification remain later design work.

## D25 — Apply the complete batch-03 authorization without widening family scope

- **Choice:** Interpret the owner's “execute the next step” response against the immediately
  preceding T39 result and exact ten-family list as approval of all ten `create_new_casting`
  recommendations. Record that authority in a separate batch-03 decision file, append it to the
  prior three-event history, and derive a new cumulative queue while keeping every release variant
  held.
- **Reason:** The prior response explicitly identified T40 as the next step, displayed all ten
  names, stated the exact ten-create/zero-hold recommendation, and explained that acceptance would
  remain family-only. The follow-up therefore authorizes that bounded action, but does not authorize
  stable IDs, release/color claims, runtime retrieval, PostgreSQL insertion, or canonical promotion.
- **Alternatives:** Leave approval only in conversation history; rewrite the T38 queue in place;
  replace prior decision history; mint searchable review entities immediately; or treat the owner
  response as variant verification. Each alternative loses auditability, reproducibility, history,
  or the explicit family-versus-variant boundary.
- **Impact:** The cumulative queue now records thirty-four completed and nineteen pending family
  decisions: four accepted existing-family merges, twenty-eight accepted new-family decisions, and
  two holds. Four ordered owner-decision events are preserved. Sixty-four release rows belong to
  completed family decisions, but all remain variant-held and promotion eligibility remains zero.
- **Deferred review:** T41 should research the next ten pending priority-2 families from the T40
  cumulative queue. Materialization of accepted review families remains a later, separate design.

## D26 — Hold same-name same-scale tools while retaining retools and scale-qualified products

- **Choice:** Build batch 04 from the checksum-verified T40 cumulative queue. Recommend creation
  when one dedicated casting lineage plus non-Fandom exact-name evidence exists, including ordinary
  retools kept on that page. Hold a grouped name when separate same-scale tools reuse the display
  name. Retain separately suffixed scale-product pages as context without automatically treating
  them as same-family conflicts.
- **Reason:** `Mazda MX-5 Miata` identifies both the 1991–2003 tool and a distinct 2025 Chimera tool.
  `Nissan Skyline 2000GT-R LBWK` identifies both the regular 2022 tool and a separate 2024 Tooned
  tool; HYW79/HYY30/HYX54 belong to the latter. A name-only family decision would hide those tool
  boundaries. In contrast, Nerve Hammer's documented retools remain one continuous page/lineage,
  and Mercedes-Benz 500 E's separately suffixed Hot Wheels XL page clearly represents an upscaled
  1:43 product rather than the queued 1:64 mainline record.
- **Alternatives:** Treat every retool as a new family; merge all exact display-name matches; hold
  any related page regardless of scale or suffix; or rely on toy numbers to silently pick a lineage
  without preserving the name conflict. These respectively fragment one lineage, collapse distinct
  tools, over-block clear identities, or make the family decision unsafe for later name retrieval.
- **Impact:** Batch 04 covers ten families and twenty-three release rows. Eight receive machine
  `create_new_casting` recommendations. Mazda MX-5 Miata and Nissan Skyline 2000GT-R LBWK receive
  holds with the conflicting pages and tool numbers preserved. Reviewer confirmation remains
  pending, all variants are held, and promotion remains zero.
- **Deferred review:** T42 must present this exact frozen split to the project owner. Resolving the
  two holds requires tool-qualified family naming or another explicit lineage key; materialization
  remains deferred.

## D27 — Preserve both batch-04 name holds in the attributable owner layer

- **Choice:** Interpret the owner's request to execute the next step against the immediately
  preceding T41 result as authorization for exactly eight `create_new_casting` decisions and two
  holds. Record the authority in a separate batch-04 decision file, append it to cumulative history,
  and keep all twenty-three release rows variant-held.
- **Reason:** The preceding handoff named both held families, linked the source conflicts, stated the
  exact eight-create/two-hold split, and identified T42 as the next action. The response therefore
  authorizes that bounded family decision. It does not resolve which Mazda or Nissan tool should own
  the staged rows, and it does not authorize stable IDs, colors, variants, retrieval, or persistence.
- **Alternatives:** Convert all ten recommendations into creations because the current toy numbers
  identify pages; discard the two ambiguous families; leave the authorization only in conversation;
  overwrite the T40 checkpoint; or immediately create catalog/PostgreSQL objects. Those choices
  respectively hide name collisions, lose pending work, weaken provenance, erase history, or expand
  a review decision into an unrequested materialization step.
- **Impact:** The cumulative queue records forty-four completed and nine pending family decisions:
  four accepted existing-family merges, thirty-six accepted new-family decisions, and four holds.
  Five ordered decision events are checksum-bound. Eighty-seven release rows belong to completed
  family decisions, but every variant remains held and promotion eligibility remains zero.
- **Deferred review:** T43 should research the remaining nine pending priority-2 families as one
  final bounded packet. The accepted review decisions still require a separate stable-entity design
  before they can enter either Dual-RAG source or PostgreSQL.

## D28 — Model renamed releases and multi-tool pages as explicit hold evidence

- **Choice:** Allow the final research batch to contain nine items instead of inventing a tenth, and
  add `renamed_existing_casting` and `multi_casting_page` evidence classes. Both classes produce a
  machine hold. Continue using `homonymous_castings` when a separate page documents a distinct
  same-scale tool under the same base display name.
- **Reason:** HYX52 is listed under `Bogzilla` but marketed as Power Wheels Dune Racer, so creating a
  new family from its release name would duplicate an existing physical lineage. Standard Kart's
  page covers both character-bearing GBG26 and driverless GRX17 tools. Nissan Skyline GT-R (BNR32)
  has a separate RLC JJY54 1:64 tool explicitly described as structurally different from the
  mainline lineage containing HYY72. None of these cases is accurately described as an ordinary
  single casting or a formal disambiguation page.
- **Alternatives:** Pad the final batch to ten; silently map Power Wheels to Bogzilla; accept the
  current toy number as sufficient family identity; classify all three as generic disambiguation;
  or create name-keyed families despite the conflicts. These options introduce nonexistent work,
  make an unapproved merge, confuse row identity with durable family identity, lose the observed
  evidence shape, or encode collisions.
- **Impact:** The final research packet covers all nine remaining pending families and thirteen
  release rows. Six receive `create_new_casting` recommendations and three remain held. The shared
  builder now supports a bounded final size and five page classifications while reproducing batches
  01–04 byte for byte. Reviewer confirmation remains zero and no variant is promotion-eligible.
- **Deferred review:** T44 must present the exact six-create/three-hold packet to the project owner.
  A later stable-entity design must decide how aliases, renamed releases, and tool-qualified labels
  become searchable without collapsing distinct physical castings.

## D29 — Close family adjudication without materializing release variants

- **Choice:** Interpret the owner's request to execute the immediately described T44 step as
  authorization for exactly six `create_new_casting` outcomes and three holds from the frozen T43
  packet. Store that authority in a separate batch-05 decision file, append it to cumulative
  history, and mark the queue fully adjudicated only because all 53 family questions now have an
  outcome. Keep all 100 release variants held and promotion eligibility at zero.
- **Reason:** T43 already exposed the complete bounded packet, the exact recommendation split, and
  the identity risks behind every hold. Applying that packet closes an auditable review stage while
  preserving the important distinction between approving a family concept and minting a stable,
  searchable entity. The latter requires unresolved choices about IDs, aliases, provenance,
  tool-qualified labels, and release variants.
- **Alternatives:** Leave the last nine outcomes only in conversation; convert all nine names into
  families; silently merge Power Wheels into Bogzilla; materialize the six accepted names directly
  into the human catalog or PostgreSQL; or promote their thirteen variants. These options weaken
  provenance, erase three identity conflicts, make an unapproved merge, or skip the stable-entity
  and variant-review boundaries.
- **Impact:** The final queue reports 53 completed / 0 pending family decisions: 4 accepted merges,
  42 accepted new-family decisions, and 7 holds. Six ordered decision events are checksum-bound.
  Every one of the 100 staged Wiki release rows remains variant-held, so the canonical catalog,
  human-backed runtime catalog, PostgreSQL snapshot, calibration data, and evaluation labels remain
  unchanged.
- **Deferred review:** Before any accepted outcome becomes searchable, a new specification must
  define the stable review-family materialization contract, including deterministic IDs, alias and
  lineage handling, provenance, hold exclusion, and a separate release-variant review path. The
  roughly 3,000-row expansion should reuse that contract rather than importing provisional research
  directly into production data.

## D30 — Materialize family decisions in a separate review registry

- **Choice:** Define a separate `pvr-review-family-registry-v1` artifact for the completed Wiki
  family decisions. Materialize the 42 accepted creations as stable family-only entities, represent
  the 4 accepted merges as links to existing human casting IDs/UUIDs, retain the 7 holds as explicit
  exclusions, and preserve all 100 source rows only as held release references.
- **Reason:** The existing human-backed catalog requires every casting to contain at least one
  human-confirmed provisional variant. The Wiki decisions approve only families. Adding placeholder
  variants would turn missing knowledge into false data; altering the existing loader to accept empty
  variants would also conflate a family registry with the current variant-backed retrieval schema.
  A separate artifact preserves both contracts and gives later runtime integration an explicit input.
- **Alternatives:** Create an `unclassified` variant under each accepted family; insert empty casting
  nodes into `human_backed_catalog.json`; immediately write rows to PostgreSQL; use display-name
  slugs as durable identity; or leave decisions only in the cumulative queue. Those choices invent
  variants, weaken current loader invariants, skip local validation, make identity depend on mutable
  text, or force every downstream consumer to reinterpret an adjudication artifact.
- **Impact:** The implemented builder emits 42 UUIDv5-backed review entities, 4 verified merge
  links, and 7 non-indexable hold exclusions. IDs derive from the immutable family review ID rather
  than the display name. The source split is 79 create rows, 9 merge rows, and 12 held rows; every
  one remains `held_for_variant_review`. Runtime retrieval and PostgreSQL remain unchanged in T46.
- **Deferred review:** The owner confirmed the RFM requirements/design/tasks by requesting T46,
  which now passes its Lite QA gate. A separate T47 contract must define family-level Dual-RAG
  documents and debug/API behavior;
  PostgreSQL ingestion and the approximately 3,000-row expansion follow held-out evaluation rather
  than being bundled into family materialization.

## D31 — Derive a typed runtime projection instead of loading the audit registry

- **Choice:** Keep the T46 audit registry unchanged and define a separate, checksum-frozen runtime
  projection containing only its 42 accepted new-family entities. Load those beside the existing
  100 provisional-variant documents in one `human-knowledge-hybrid-v2` sparse/dense/RRF index, and
  expose a discriminated debug union under the existing `human_knowledge_candidates` list. Skip all
  4 merge links and 7 holds as new documents.
- **Reason:** The registry explicitly says it is not runtime-loadable and retains held release
  provenance that must not become searchable. A field-allowlisted projection preserves that audit
  contract. Typed documents avoid inventing provisional variants, while a unified pool keeps one
  second-RAG ranking/limit instead of presenting two incomparable debug lists. Merge names already
  have existing human-backed variant documents, so another family document would duplicate identity.
- **Alternatives:** Load the audit registry directly; rewrite its T46 usage boundary; coerce every
  family into the existing variant schema; expose a separate family-candidate API list and retriever;
  or immediately persist the families in PostgreSQL. These options respectively expose held fields,
  invalidate frozen T46 evidence, fabricate identity, split ranking/limits, or combine unmeasured
  retrieval quality with persistence and scale changes.
- **Impact:** T47.1 now implements and freezes the 42-document family projection. Each document uses
  only brand, approved name, and aliases as future searchable fields; source record IDs remain
  non-searchable provenance. The builder accounts for but excludes 4 merge links and 7 holds and
  copies no release details, decision reasons, or evidence URLs. The proposed runtime pool remains
  142 globally unique documents—100 provisional variants plus these 42 review families—but the
  T47.2 now strictly validates that artifact and its manifest, then combines 100 variant documents
  and 42 family documents behind common `knowledge_id`, `knowledge_uuid`, and `searchable_text`
  properties in `human-knowledge-hybrid-v2`. Canonical candidates remain the sole input to
  confidence and final identity. Runtime verification retrieves 42/42 exact family queries within
  Top-5 (worst rank 2), keeps the existing BMW variant at Top-1, and leaves Proton Saga as
  noncanonical `no_match`. T47.3 completes the public boundary with two strict Pydantic/OpenAPI
  branches selected by `knowledge_type`. The service now serializes the already bounded mixed
  ranking directly: variants retain variant IDs, families retain only review-family IDs, and the
  debug payload publishes the family projection version. The UI renders both branches using text
  nodes and explicitly labels family-only evidence without inventing a release variant. T47.4's
  requirement-by-requirement Lite review passes all sixteen requirements, reproduces the full data
  chain, and confirms the pre-T47 canonical catalog, benchmark, calibration/policy, migrations, and
  PostgreSQL implementation remain unchanged.
- **Deferred review:** Exact-name self-retrieval proves wiring feasibility, not generalization. A
  held-name query can still retrieve an unrelated accepted family through shared tokens, so T48 must
  use an independently authored casting-grouped holdout before any quality or production claim.
  PostgreSQL/pgvector integration and the approximately 3,000-row expansion remain after that gate.

## D32 — Freeze an output-blind family challenge before scoring or persistence

- **Choice:** Define `family-retrieval-holdout-v1` as a separately authored, owner-approved,
  test-only benchmark against the already frozen `human-knowledge-hybrid-v2`. Use exactly 105 cases:
  two positive styles for each of 42 accepted families, 4 accepted-merge controls, 7 held-family
  controls, and 10 unrelated/no-overlap controls. Freeze queries and labels before the evaluator
  exposes any candidates, ranks, scores, or pass/fail result.
- **Reason:** T47's 42/42 exact-name result proves indexing but reuses the searchable label and is
  therefore not independent evidence. The 2025 staging rows are contractually staging-only, and the
  family projection is excluded from evaluation ground truth. A new authoring/approval layer tests
  noisy retrieval without rewriting those older usage boundaries or promoting family decisions
  into canonical labels.
- **Alternatives:** Rebrand the exact-name smoke matrix as accuracy; score the existing Fandom rows;
  scrape live marketplace titles during each run; generate thousands of template mutations; or
  persist first and evaluate later. These respectively create leakage, violate frozen usage scope,
  lose reproducibility/privacy control, substitute volume for independent judgment, or scale an
  unknown error profile.
- **Gate:** Precommit Recall@5 `>=0.85`, Recall@1 `>=0.65`, MRR@5 `>=0.75`, style Recall@5
  `>=0.75`, family coverage@5 `>=0.90`, merge-control Recall@5 `=1.0`, zero forbidden family hits,
  and zero unrelated non-empty results. A valid run below any gate is a truthful FAIL, not permission
  to edit the test set.
- **10x consideration:** A 105-case manually reviewable set is preferred over a 1,000-case synthetic
  generator. It covers every known family and governance outcome while concentrating review effort
  on two qualitatively different query styles. If the corpus grows roughly 10x toward 3,000 rows,
  this benchmark becomes historical evidence and a new scale-representative holdout is required.
- **Most likely failure:** Lexical-variation queries may lose every shared token, especially for the
  four single-token families. The current sparse and feature-hashing paths both start from normalized
  tokens, so such cases may return no candidate. T48 must report this failure class rather than
  weaken cases or thresholds after scoring.
- **Impact:** The draft specification introduces no query data, evaluator result, model change,
  canonical identity, variant truth, or PostgreSQL row. After owner confirmation, T48.1–T48.3 freeze
  the contract, query pack, and labels before T48.4 evaluates; T48.5 decides whether T49 may start.
- **Deferred review:** Neural/fuzzy retrieval, query expansion, PostgreSQL/pgvector persistence,
  production thresholds, live marketplace evaluation, and the approximately 3,000-row expansion
  remain separate decisions after the v1 result is understood.

## D33 — Separate query freezing from label approval and benchmark construction

- **Choice:** Implement one fail-closed builder with three explicit phases: freeze/check the
  output-blind query pack, validate a separately checksum-bound project-owner decision file, and
  only then build/check the labeled benchmark. Freeze both data inputs and the source files that
  implement normalization, hashing embeddings, and Human Knowledge retrieval.
- **Reason:** T48.2 must be able to prove its 105 queries are structurally valid without creating
  labels or running retrieval. If the only command required owner decisions, query authoring could
  not be frozen independently. Data checksums alone are also insufficient because changing the
  normalization or ranking code would silently change the system under test while retaining the
  same catalog version.
- **Alternatives:** Combine query authoring, approval, and scoring in one command; record only model
  names without source checksums; accept train/dev cases for convenience; or write partially valid
  outputs and repair them later. These options create output leakage, permit implementation drift,
  weaken the test-only boundary, or let invalid input replace known-good evidence.
- **Impact:** `build_family_retrieval_benchmark.py` now validates exact 105/84/4/7/10 composition,
  full family/control coverage, non-copying and lexical/no-overlap rules, source manifests, fixed
  v2 parameters, all 105 owner approvals, and every excluded use. Every output file is replaced
  atomically only after all validation succeeds, and `--check` modes never mutate files. Six new
  contract tests pass as part of the 190-test suite. No official query, label, retrieval output,
  canonical record, or PostgreSQL row was created.
- **Deferred review:** T48.2 must author and commit the official query pack without inspecting
  retriever output. T48.3 then requires the project owner to review all 105 cases before the first
  benchmark can be built; scoring remains T48.4.

## D34 — Preserve hand-authored query intent as a reproducible pre-score source

- **Choice:** Store the 105 independently composed synthetic queries in a deterministic authoring
  script keyed only by review identity, then freeze its validated JSON output and manifest in a
  separate commit before owner labeling. Use one marketplace-noise and one lexical-variation query
  per accepted family, explicit governance controls, and opaque invented tokens for unrelated cases.
- **Reason:** Hand-editing a 77 KB JSON artifact would make accidental ID/order/schema mistakes
  difficult to audit, while generating queries from automatic templates would make case volume look
  more independent than it is. A small source map preserves the exact human-authored wording and
  lets `--check` prove reproducibility without importing or invoking retrieval code.
- **Alternatives:** Scrape live marketplace listings; reuse Fandom titles or prior human queries;
  create all questions through one mutation template; omit the authoring source after writing JSON;
  or run retrieval while revising weak-looking questions. These choices respectively harm
  reproducibility/privacy, leak indexed wording, overstate diversity, weaken provenance, or directly
  contaminate the holdout.
- **Impact:** The frozen pack contains 105 test-only cases and SHA-256
  `26e244c04325f7909fb222b6cdd32ee2301253db17f0b8b97cf2f63ac4358733`. All 42 families have both
  styles; Bogzilla, Crescendo, Draftnator, and Haulerback have full-token spelling disruptions; all
  controls are complete; and all ten unrelated queries have zero corpus-token overlap. Eight focused
  tests prove pack/manifest validity and non-mutating reproduction. No retrieval output or owner
  label was generated.
- **Deferred review:** The project owner must review every frozen query/reference pair. T48.3 may
  create labels only against this exact checksum; any wording change requires a new freeze and new
  review before scoring.

## D35 — Bind the owner's proceed instruction to the already frozen 105-case pack

- **Choice:** Treat the project owner's instruction to perform the next step, given immediately
  after the complete frozen query/reference evidence and checksum were presented, as approval of
  all 105 unchanged pairs. Record one attributable approval per case and build the labeled but
  unscored benchmark only against query-pack SHA-256
  `26e244c04325f7909fb222b6cdd32ee2301253db17f0b8b97cf2f63ac4358733`.
- **Reason:** The preceding handoff explicitly said T48.3 required owner confirmation, linked the
  human-readable review document, described every case class, and stated that proceeding would
  create labels but not run retrieval. The follow-up instruction therefore authorizes this exact
  bounded review action; it does not authorize changing questions, canonical promotion,
  persistence, or model tuning.
- **Alternatives:** Ask the owner to repeat the same confirmation phrase; infer labels without a
  recorded authority; approve only positive cases and leave controls pending; regenerate questions
  during labeling; or combine approval with immediate scoring. These options add no meaningful
  consent, weaken attribution/completeness, allow leakage, or collapse the designed pre-score gate.
- **Impact:** All 105 decisions now record `project_owner`, second-precision UTC time, `approve`, a
  case-specific reason, and a type-safe expected identity or negative expectation. The decision
  artifact hash is `d22b96bb16cd9cb9e19f4a4723a41b653da7b4961b5b588f6f636e1b37e1bad1`.
  The resulting frozen benchmark hash is
  `440246fb6a3b38f56fc25c1ec939d53d6cfc4457fed738aad561899325808afd`; it contains no candidate,
  rank, score, metric, or verdict. Ten focused checks reproduce the approval and benchmark bytes.
- **Deferred review:** T48.4 is now permitted to implement and run the read-only evaluator for the
  first time. Its result must use the precommitted gates, and a FAIL cannot trigger edits or tuning
  on this v1 holdout.

## D36 — Preserve the lexical-quality failure and block T49

- **Choice:** Close T48 engineering verification while preserving the scored result as
  `verdict=FAIL`. Keep `human-knowledge-hybrid-v2` and the 42 family documents debug-only, prohibit
  any tuning or model selection on `family-retrieval-holdout-v1`, and do not begin T49 PostgreSQL/
  pgvector persistence or the approximately 3,000-row expansion.
- **Reason:** Eight of nine gates pass, but the precommitted all-gates contract requires both styles
  to reach Recall@5 `>=0.75`. Lexical variation recovered only 31 of 42 families (`0.7381`), one
  successful case below the minimum. Reinterpreting the strong overall `73/84` Recall@5 as a PASS
  would erase the exact weakness that style-level gating was added to expose.
- **Alternatives:** Round 73.81% up to 75%; lower the threshold; remove one failed query; widen K;
  add fuzzy or neural retrieval and rescore v1; or persist first because the other gates passed.
  All would violate the pre-score contract, tune on the final test, or scale a known weakness.
- **Impact:** T48 closes with 201/201 executable tests and all reproducibility, canonical, T47,
  compilation, Compose, and scope checks passing. The model-quality record remains FAIL with eleven
  lexical misses, zero forbidden-family hits, and zero unrelated non-empty results. No runtime,
  canonical, persistence, or benchmark file is modified by the closure decision.
- **Next review:** Specify a retriever-redesign feature using separate development evidence. If the
  retriever changes, author and owner-approve `family-retrieval-holdout-v2` before final scoring.
  T49 remains blocked until that unseen gate passes.

## D37 — Add deterministic character candidate generation before considering neural retrieval

- **Choice:** Propose `human-knowledge-hybrid-v3` as the existing token-sparse and `hashing-v1`
  dense Human Knowledge retriever plus a character n-gram TF-IDF identity channel. Build an inverted
  posting index over allowlisted identity names, union exact-token and threshold-qualified character
  candidates, dense-rank that bounded union, and fuse available ranks with weighted RRF. Select only
  the character floor/weight from a predeclared 21-configuration grid on a separate development set.
- **Reason:** The v1 failure class is spelling, abbreviation, punctuation, spacing, and numeric-form
  disruption. Current dense character information is inaccessible until a shared token first admits
  the document. A character channel directly fixes that architectural bottleneck while retaining
  deterministic offline behavior and inspectable scores. Development/final separation prevents v1
  or the future v2 holdout from becoming a tuning set.
- **Alternatives:** Score current hash vectors over all 142 documents; use edit-distance query
  rewriting; reserve fixed family slots in Top-5; or immediately add a sentence-transformer. These
  respectively lack an interpretable admission floor, can silently rewrite unknowns into known
  identities, manufacture a type bias, or add model/cache/license/memory complexity before a
  spelling-oriented deterministic baseline is tested.
- **10x consideration:** Gram postings avoid unconditional document comparison and a disclosed
  synthetic 3,000-document smoke must pass before final evaluation. This predicts algorithmic cost
  only and does not replace T49 PostgreSQL design or real-data measurement.
- **Most likely failure:** A low similarity floor improves typo recall but can violate unrelated or
  held-family safety; a high floor can recreate the original miss. Safety gates filter candidates
  before quality objectives, and no qualifying configuration means STOP rather than grid expansion.
- **Impact:** HRR-T1 has frozen the development contract and HRR-T2 has implemented the experimental
  mechanics behind a checksum-bound artifact opt-in. V2 remains active because no configuration has
  been selected and no runtime artifact exists. HRR-T3 must evaluate exactly the frozen 21 options,
  publish every result, and either freeze one qualified artifact or stop with FAIL before any new
  output-blind v2 holdout is authored.

## D38 — Preserve the fixed-grid FAIL and require identity/cost redesign

Choice: close HRR-T3's engineering checkpoint, retain development selection FAIL with no winner,
leave v2 active, and block HRR-T4–T6/T49. No grid expansion, threshold relaxation, nearest-to-pass
selection, final-query authoring or database promotion follows this result.

Reason: all 21 settings recover 164–168/168 positives, ≥38/42 per style and 4/4 merge controls, with
zero forbidden families, but all produce 10/20 unrelated nonempty results and fail both p95 budgets.
The recorded generic-00 result at the highest floor returns candidates using exact `box`, `collector`
and `blue` evidence with no character ranks. The existing token path can therefore admit generic
text independently of character threshold. Synthetic shared identity forms also expose costly
posting-derived comparisons: 419,820 entries and p95 337.15–377.28 ms, versus the 150 ms gate.

Alternatives rejected: waive safety because positive development recall reaches 100%; adjust only
the character floor; choose the maximum-MRR failing setting; rerun v1 as a v3 comparison; persist
before quality; or change scoring after viewing this report. These either conceal the observed
failure, miss the exact-token cause, tune on held evidence or violate the acceptance contract.

10x/most likely failure: shared-gram candidate growth and long identity-form comparisons remain a
cost risk even with postings. A new design must bound comparison work and require identity-bearing
eligibility without manufacturing family quotas. Its method and any new grid must be declared
before new configuration output; before/after cost must be measured. No neural model or revised
threshold set is selected by this decision.

Impact: 236 tests and report/source/arithmetic checks pass, but engineering correctness does not
convert model safety/cost into PASS. Real p95 is 29.37–36.60 ms (25 ms budget); synthetic p95 is
337.15–377.28 ms (150 ms). No runtime artifact or real rows were added. The complete raw evidence
is in `reports/family-retrieval-development-v1/selection.json`, SHA-256
`dcc0cd4e09ec5b20862cfee39b90d65a12bbd48a80f7da29c0fbacb0da267853`.

Next review: return to Phase 1 for a new Lite identity-admission/bounded-scoring design. Preserve the
old v1 and current development reports; a later qualified freeze still requires a newly authored,
owner-approved unseen final holdout before T49 can be considered.

## D39 — Proposed isolated v4 identity-core admission and exact posting accumulation

Status: PROPOSED, pending project-owner confirmation of requirements/design/tasks. This is a new
design after D38's stop, not permission to alter the frozen v3 grid or reinterpret its FAIL.

Context: v3 generic-00 at floor 0.55 returns documents through broad exact tokens with no character
rank; changing character admission alone cannot remove that path. The character implementation
gathers posting candidates but still computes query-window × document-form comparisons, and sparse
frequencies are scanned per query. Published cost fails both budgets. These observations justify
a structural proposal; they are not a new profile or proof of the proposed method's speed.

Proposed choice: add separate `human-knowledge-hybrid-v4` modules while keeping source-bound v3,
normalizer and hashing files unchanged. Candidate identity fields narrow to provisional casting and
family casting/approved aliases. A frozen global whole-token noise policy applies equally to query
and identity cores. Exact admission requires a complete core, while typo/spacing rescue uses full-
norm character evidence. Precomputed weighted form-level gram postings accumulate exact cosine
scores directly; query unknown grams remain in the norm. Hard work limits abort the entire Human
result with query-local debug counters, never emit partial scores. No family quota or canonical
authority change. A new mandatory-evidence v4 artifact is required for opt-in.

Alternatives: raise only character floor (does not close broad token admission); stopwords over full
human listing text (other irrelevant terms still admit); approximate character shortlist (can hide
lost targets before exact scoring); reserve family slots (policy-manufactured ranking); immediately
add a neural model (dependency/artifact cost without closing admission or comparison requirements).
Keep these alternatives for a later explicit decision if the exact bounded baseline fails.

The same 21 settings and gates are retained for an architecture-focused experiment. The existing
199 cases are explicitly viewed, leaky development data reused for diagnostics/configuration, not
a fresh blind dataset. A new protocol must freeze policy/formula/limits/workload/source hashes before
v4 outputs; old final v1 is never a selection source. Synthetic scale adds 100 target-bearing probes
to the original 20 queries and requires correct exact/contextual/typo retrieval, so budget abstention
cannot masquerade as sufficient performance.

| Dimension | Anticipated benefit and unverified cost |
|---|---|
| Safety | Broad listing tokens lose independent admission; noise/core collisions can still harm identity distinctions. |
| Quality | Character rescue remains; removing human-label admission synonyms and unknown-gram normalization may lower recall. |
| Cost | Direct accumulation removes pair loops and per-query DF scans; common postings may still breach limits/timing. |
| Maintainability | Separate version preserves historical checks; new protocol/loader adds bounded versioning work. |
| Scalability | Explicit form/window/posting limits expose 10x growth; exceeding limits is abstention, not an untested scale PASS. |
| Observability | Query-local work/abort counters expose cost; no shared last-query state or raw-title logs. |

Most likely failure: legitimate names lose noise tokens/synonyms, or frequent grams cause budget
abstention and positive misses. Neither outcome can waive gates. Validate identity cores/collisions
before output; verify scorer against an exact oracle; measure full before/after query workloads.
If policy/limits/workload must change after output, preserve FAIL and freeze another protocol.

Impact now: documentation only. No code/provider/data/runtime changes, no v4 outputs/quality PASS,
no new final authoring, no actual ingestion/default deployment. G1* remains pending owner approval.
Next permitted task after approval is IBR-T1 protocol validation/freeze/commit, not immediate scoring.

## D40 — Confirm D39's exact specification and freeze before v4 output

Status: ACCEPTED for IBR-T1. The owner's `執行下一步` response to the explicit three-spec confirmation
handoff confirms commit `880e4f5` and its exact requirements/design/tasks hashes. D39's proposed design
is accepted under the unchanged Lite task order, not authorization for scoring, ingestion or deployment.

Choice: preserve original approved text in checksum-validated in-project snapshots, record separate
owner approval/time/scope, and freeze a deterministic protocol/core audit/workload/manifest before
any v4 output. Runtime rules remain fixed to the approved global noise set, casting/alias fields,
new formula, original 21 settings and all prior gates. Freeze refuses to overwrite different
existing artifacts; checks use snapshots without requiring old Git history. Live progress/status
edits therefore do not rewrite the approved baseline or break its artifact references.

Evidence: all 142 documents retain valid cores, with 284 forms, max 2/document, zero cross-casting
collision and two same-casting variant collision groups. Real/scale query forms peak at 90/60 below
256. Synthetic 3,000 documents have 12,000 forms/max 4 per document. Workload counts are exactly
20 original cost, 60 exact, 20 edited, 20 contextual; positive target IDs/UUIDs and correctness gates
are frozen. Twelve new focused tests and 248 full tests pass, and old source-bound reports still check.

Trade-off preserved: approved synthetic casting cores are numeric-only and edits affect the removed
`Scale` wrapper. This workload catches empty-only fast outputs, not retained-core spelling quality;
do not generalize it or secretly replace it after outputs. Static form/gram counts are not measured
runtime memory/cost. Genuine four-style real development and new unseen final quality remain gated.

Alternatives rejected: rewrite proposed historical snapshots as though they had already been approved;
bind mutable task checkboxes as immutable source; silently drop/merge cores; improve scale probes
without recording a changed design; or run retrieval now to see which rule passes. Each weakens
attribution, artifact stability, identity preservation or pre-output separation.

Impact: protocol SHA-256 `31802be99f02698423c4526bbd8752e6f517fcbef8ca8080926d019f55083fde` is
frozen with builder/corpus/development/report/spec/source bindings. No retriever/service/model/data-
catalog change, v4 output/artifact/latency claim, final query authoring or SQL expansion. Default v2
and T49 blockade remain. Next: IBR-T2 exact posting/oracle and isolated runtime implementation;
limits/policy changes would require a new versioned decision/protocol, not an after-output edit.

## D41 — Isolate v4 query arithmetic from qualified-evidence loading

Status: ACCEPTED for IBR-T2 implementation only; no selected/default v4 release.

Choice: retain the owner-approved identity/token/form-posting model in a new runtime module and
place strict artifact/raw-report validation in a second new module. Query-local frozen work values
return beside candidates; no shared `last_work` property or service mutation. Complete human aborts
do not alter canonical status, while corrupted index/evidence/provider state fails dependency readiness.

Reason: old v3 sources/report hashes must stay valid, and mixing evidence loading with hot-query math
would make source provenance harder to test. Separate opt-in requires every protocol/source/fixed
parameter/full raw report/winner check; runtime cannot activate an arbitrary floor/weight or a failed
configuration. Tiny unit/API configurations remain ephemeral test construction, not selected artifacts.

Alternatives: edit the old v3 loader/scorer (breaks published provenance); shared mutable debug counters
(concurrent requests can overwrite evidence); silently revert to v2 on a requested v4 failure (misstates
active configuration); or approximate eligibility/type quotas (violates exact/admission contract).
Direct accumulation is chosen for mathematical verifiability, not an unmeasured speed promise.

Evidence: 65 focused and 311 full tests pass, independent cosine/rank/cap/authority checks and old
source-bound report reproduction pass. Docker copies source-bound reports/builder and admits the
builder through `.dockerignore`; static context/Compose checks pass, no rebuilt runtime claim.

Accepted costs: index initialization retains per-form weights and dense vectors; common gram postings
can still reach the cap. Noise removal/synonym loss/core collisions and numeric-only synthetic probes
remain known risks. A qualified artifact validates a full 21-grid report at startup, adding readiness
work but avoiding query-time report replay. Complete report execution/replay is deferred to T3.
No policy/grid/ceiling change, selected artifact, final authoring or SQL expansion follows this decision.

## D42 — Select the frozen v4 development winner without activating it by default

Status: ACCEPTED for IBR-T3 experimental artifact; final/T49/default deployment still gated.

Choice: run exactly the owner-frozen 21-setting architecture experiment once, retain complete raw
results and apply every quality/safety/cost/scale-correctness gate. All qualify; the predeclared MRR,
Recall@1, higher-floor/lower-weight ordering chooses **0.50 / 1.0**. Do not choose 0.55 merely because
it is the highest floor: it loses two positive edit/abbreviation cases and has lower ranking quality.

Evidence: selected R@5 168/168, R@1 165/168, MRR0.9911, styles42/42, merge4/4, forbidden0,
unrelated0/20; p95 real/scale2.07/45.14ms; synthetic60/20/20 target hits. Original-20 scale p95
61.22ms is separately comparable to the published v3 diagnostic, not the easier aggregate120.
329 tests pass; strict raw arithmetic/source/winner replay and genuine runtime/API loading pass.

Change from D41: previously no qualified v4 artifact existed; now a source/protocol/corpus/full-report
bound artifact is frozen in committable `config/`. This enables explicit debug evaluation, not a
default version switch, independent final PASS or real expansion. No scoring/policy/cap/grid change.

Method: standard-library evaluator, existing types/hashing, one retrieval process and raw timings.
Exclusive temp-byte validation/publication prevents destructive artifact replacement; FAIL returns
before directory creation. Runtime validator additionally recomputes work/subgroup totals, finalized
before real output. Docker read permission on copied public evidence handles host 0600 generated files
without checksum changes; static packaging is not a fresh container-run claim.

Alternatives rejected: silently extend the grid, select nearest failing setting, suppress abstentions,
compare only easier synthetic queries, overwrite v3 history, or call development success final quality.
No neural dependency/API/download is needed for this controlled architecture stage.

Limits and most likely next failure: viewed identity-derived queries can overstate generalization;
noise policy can lose unseen real names; synthetic number-only/wrapper-edit probes are limited.
Non-isolated timings include a brief initial verification-process overlap and are not causal/production
proof; no samples were resampled. At 10×, common postings may still cap-abstain. New independent
owner-reviewed questions and fresh runtime/regression closure remain necessary. Commit winner before
authoring and stop for owner approval before labels/retrieval; only final/closure PASS authorizes T49 design.

## D43 — Freeze new final questions after winner commit; stop before owner truth

Status: ACCEPTED for IBR-T4 query preparation only. Owner relevance approval/labels/final score pending.

Choice: explicitly compose 105 synthetic questions after committed winner `a9a3730`, keeping the
same 42 families/two positive styles and 4/7/10 controls. Freeze every query/intended-registry-reference
pair, case/source/pack hash and human-readable owner table. Do not derive questions by a uniform
mutation program, consult new retrieval results, label automatically or treat generic proceed as
confirmation of previously unseen pairs. Output-blind concerns these new results, not author knowledge
of old development/policy; same-family synthetic final is not unseen-casting/population evidence.

Method: standard-library explicit literal strings and Git/JSON/hash checks; unchanged normalization
and identity-noise policy only for static reuse detection. Reject normalized/compact old/indexed
query equality and nonempty old question-core equality. Static checks are stricter than raw equality
but do not prove semantic independence or remove all author bias. Ordinary unrelated nouns are
chosen for nonvehicle relevance, not experimentally low character scores. Owner judgment remains
required before expected labels. No new model/network/dependency, catalog mutation or agent.

Provenance: compare all selected/runtime/evaluator/protocol/corpus/dedup input bytes with the winner
commit and verify new pack absence there. Stage pack/manifest/owner-review as one directory and
publish after validation, preserving invalid/preexisting artifacts. Twenty-two new tests and 351
full tests pass, with one existing warning; no new-final retrieval or label artifact is created.

Correction preserved: initial unapproved metadata named 0.90 coverage `positive_coverage`. Reading
the inherited gate/formula established **family_coverage_at_5 over 42 groups**. Preserve draft/source
snapshots under `family-retrieval-v2-superseded-draft-01`, re-freeze the identical 105 cases with the
correct name before owner handoff. This changes a misleading metric name, not the approved threshold,
query content/model or output-based selection. No initial-draft approval/score occurred.

Authoritative query SHA: `b23b69912c678c027461c96eb23f113484c5a8ed6218c06d90026704abe5102b`.
Owner must explicitly confirm these 105 pairs/checksum (or identify cases for versioned revision).
Next separate phase records real approval/attributable labels and commits benchmark before one final
score. Avoid closest-result tuning on final FAIL. Most likely failure: natural abbreviations/numeric
forms or broad negative character overlap generalize poorly despite perfect dev Recall@5. At10×,
posting limits/generalization still need evidence. Defaultv2, final/runtime closure and T49 remain gated.
# D44 — Separate approved family labels from immutable question/runtime artifacts

Status: accepted,2026-09-14; Lite IBR-T4 only. The owner confirmed targets, asked about distinguishing
features, then agreed to proceed after the family-versus-variant scope explanation. That actual
context authorizes whole-pack family labels, not canonical/color/wheel/tampo/release truth.

Use a new builder/module and one exclusive complete `approved/` directory rather than modifying
source-bound question author/runtime modules or independently writing partially visible files.
Derive positive ID/UUID, merge casting ID/UUID and held/unrelated governance labels only from
unchanged frozen registry/projection/human inputs. Record actual excerpts and recording time;
unavailable message time stays null. Validate exact type-sensitive objects/source hashes and
commit-before-score provenance, without retrieving new questions.28 new/379 full tests PASS.

Trade-offs: conversation records are not signed identity proofs;105 pairs approved as a whole pack,
not individually authored new labels. Historical query pending flags remain immutable and the
new validator owns current approval state. At10×, hashing/validation scales with artifact bytes;
no new index/model/database choice needed. Most likely semantic failure is treating a family hit
as a proven release match, expressly excluded here. Scope/integrity/safety/auditability/operational
cost/extendability assessment: adequate for Lite family evaluation, insufficient for production
variant accuracy. Final quality/runtime remains unrun; originalFAIL/defaultv2/T49 restrictions stay.
See `docs/evidence/family-retrieval-final-v2-label-freeze.md` for produced evidence.
# D45 — One-shot family final and packaging-only evidence-root correction

Status: accepted,2026-09-14, Lite IBR-T5. Benchmark87bbd19 and evaluatorb86578c were committed
before exactly105 final calls. Preserve raw outputs before label scoring, fixed9 gates/denominators,
all fourlexical misses and all failures. Raw-derived final gates PASS80/84@5,77/84@1,MRR.93254,
family42/42,merge4/4,forbidden/unrelated0; no final-set tuning or default switch.

The successful host tests did not establish container readiness. Actual non-root/read-only HTTP
revealed installed-package ROOT differs from/app evidence. Select DockerPYTHONPATH=/app/src,
not edits to pinned loader/retriever or evidence bypass. Dependencies remain installed; exact
bundled sources now derive the correct root. At10×, this does not alter postings/cost/model rules.
Keep the old failing image/report and new source/image-bound successful report. Relocation alone
was an invalid stale verifier fixture, corrected to mandatory evidenceSHA corruption;503 gates
unchanged. No final retrieval rerun occurred.32focused/411full tests and DockerHTTP PASS.

Trade-offs: source-tree execution couples this image to the existing repo-root evidence layout;
a standalone-wheel resource design would need a new source/protocol/artifact version and must
not be silently introduced after final scoring. Separate integrity preflight validates labels, but
collector only accesses query signals and publishes raw105 outputs before scoring. Most likely
remaining semantic failure is assuming family success proves real variant accuracy. Scope,
integrity,safety,auditability,cost,extendability: adequate for Lite family closure; population and
release/color/wheel/tampo accuracy still unevaluated. T49 DESIGN ONLY, no SQL/default deployment.
See `docs/evidence/family-retrieval-final-v2.md` for outputs, measurements and actual failure history.
# D46 — Split T49 knowledge persistence from real release review and quota expansion

Status:PROPOSED,2026-09-14; owner requirements/design/tasks unconfirmed. af27dfe authorizes design,
not actual collection or DB writes. Read-only source/model audit shows142knowledge docs,100heldWiki
rows with all color-null/no wheel/tampo fields, and legacy seven-field identity missing those
discriminators. Family PASS cannot substitute for release truth or3,000approved products.

Propose independent versioned hk snapshot tables for100provisional+42family docs and separate
release-source/field-evidence/review records. First task local-only import PLAN; further isolated
DB/profile/cost/source access/release/identity/evaluation work needs explicit boundaries. JSONB
preserves current typed payloads; normalized field evidence makes unknown/conflict/review visible.
Reuse PostgreSQL/SQLAlchemy/Alembic proposals, not canonical tables or silent scored-module edits.
Files remain valid default. No ANN/neural/image/OCR/promotion included.

Trade-offs: multiple schema lanes add some implementation overhead, but prevent unknown fields
from creating false variant equivalences or unreviewed rows entering final UUID answers. Future
identity-v2 preserves old UUIDs, not in-place field additions.3,000goal counts deduprealstaged releases
separately from confirmed/canonical products; report100/500/1,500/3,000milestones without synthetic
padding. At10×, review/source/SQL/network costs need measured protocols. Most likely failure is
mistaking source confidence or persistence for human-verified exact release identity. Scope,
integrity,safety,auditability,cost,extendability: adequate planning boundaries; implementation and
source-specific rights/variant accuracy remain unverified. GeneralAPI etiquette is not Fandom
permission; tool402fetch failures retained as access uncertainty, not bypass authorization.
See `docs/evidence/t49-planning-scope.md`; pause at owner G1* before product implementation.

# D47 — Pin and roundtrip a separate local human snapshot plan before persistence

Status:ACCEPTED for local T49.1 only,2026-09-14. Owner execution after detailed draft explanation
authorizes the first local task; no separate sequential G1 confirmations or full schema agreement
are invented. Later database/collection/profile/release lanes remain gated. D46's table designs
remain proposed; this step does not implement them or remove source ingestion exclusions.

Select a new standard-library-only plan module/CLI, reusing the existing typed loader read-only.
Pin12immediate local inputs and reconstruct the whole deterministic plan for checks. Preserve both
exact typed fields and original casting/variant/family/registry metadata:typed payload alone would
drop failure categories, family-only level, provenance and held-release review decisions. Snapshot
ID derives from content, not a new canonical UUID. Future source changes need a reviewed v2 pin
set rather than mutable v1 checksum updates. Existing scored modules remain byte unchanged.

Trusting only mutable manifests or self-rehashed payloads was rejected because changed data and
manifest can agree while violating the approved baseline. JSON checksum comparisons are
type-sensitive, soFalse cannot masquerade as0. File publication uses an exclusive new directory,
checks both JSON/Markdown and cleans only task-owned files. A process kill may leave incomplete
output; check rejects it and repeat refuses it. This is not database crash-atomicity/idempotence.

Trade-off:raw casting/registry evidence duplicates some source data, acceptable at142docs for
auditability. At10×, plan file size and source-version review grow; actual query/SQL/posting cost
still needs its own protocol, not a claim from fast offline validation. Most likely failure remains
mistaking stored human evidence for canonical variant truth. Scope/integrity/safety/auditability
PASS for this local artifact; cost/extendability limited to versioned planning, not DB/real3krollout.
37focused/448full tests and plan/checker PASS; see `docs/evidence/t49-1-execution-scope.md`.

# D48 — Verify additive human snapshot storage in a fresh disposable PostgreSQL lane

Status:ACCEPTED for isolated T49.2 test only,2026-09-14. Owner「執行測試」after the explicit
environment proposal authorizes tmpfsDB/newinternalnetwork/runner/testbaseline/ownedcleanup;
not production/defaultprofile/collection or fictional sequential broadG1 approvals.

Select existing PostgreSQL16/SQLAlchemy2/Alembic stack with additive0002 independenthuman tables
and a new test-only repository. Preserve canonical0001, scored API/config/retrievers, oldUUIDs,
source restrictions and frozenplan/final artifacts. Store entire plan header plus exact typed/raw
child JSONB and checksums/ordinal/import timestamp. Serialization retains nulls and review status;
samecasting evidence is not verified release equivalence. No embedding/release table yet.

Use one engine.begin transaction and SHARE ROW EXCLUSIVE locks on both smallhuman tables.
This closes first-insert races without overwrite-upserts; repeat reads all142rows before verified
no-op. ExplicitID+hash repeatable-read/read-only hydration avoids latestsnapshot/tornreads/fallback.
Literal authorization/name/actualdatabase guard and fresh isolated resources avoid an accidental
existingDB target. Applicationimmutability is not superuser-proof; directcorruption is detected,
not repaired. JSONB shape/unique/FK/count constraints complement source-pinned wholeplan checks.

The host lacks SQLextras and some sources are600mode. Choose byte-exact readable private staging
with existing SQL-enabled nonrootimage, not host dependency installation or chmod originalinputs.
54source fingerprints/imageIDs/full stdout-stderr preserved. Internalnetwork/nohostport/tmpfs and
exactownership cleanup keep this test distinct from working data. Old T04verification is0001-bound;
do not silently change its historical assertions or claim itsheadcheckPASS for0002. New verifier
covers0001→0002→0001→0002 while preserving canonical fixtures throughout.

Trade-offs:serializedtablelocks/rawprovenance duplication are acceptable at142docs; at10× need
measured contention/storage/query protocol, not inferred performance. tmpfs excludesdurability/
powerloss testing; processkill may leaveownedresources. Most likely semanticfailure remains
treating persistent familyknowledge as verified producttruth. Scope/integrity/safety/auditability
PASS for isolatedSQL; cost/extendability limited until T49.3 protocol.25new/473full tests and first
actualSQL invocation PASS,71visible-doc uniquefault fullrollback, concurrentinsert/noop and repeat
timestamps identical, canonical7tables unchanged, ownedcontainers/network removed. See
`docs/evidence/t49-2-human-knowledge-postgres.md`; no real3k/production/defaultrollout claim.

# D49 — Propose an explicit human-storage profile with live full-snapshot integrity gating

Status:PROPOSED,2026-09-14. Currentnextstep follows planninghandoff; draftonly, ownerG1WAIT.
Do not mark fullT49.3complete or claim approvedprotocol/newadapter/SQL/cost results.

Propose newcompositional appfactory via existingservice_factory/constructor, twofile/DB profiles
and newstorageartifact/sourcebinding. Keep oldAPI/config/service/v4/identity/T49.2/artifacts unchanged.
Reuse unchanged0.5/1.0/hash192/RRF60/identityadmission/limits. V4constructor pins the oldmathprotocol;
newstorageprotocol must be referenced separately, not overwrite thatfield or relax oldartifact exclusions.

Startup builds a142docmemoryindex; eachhealth/validresolve fullyrevalidatesselectedsnapshot readonly
beforeusingcache. This catches poststartDBloss/header/child corruption rather than declaringcached
data healthy while configuredstorage is broken. SELECT-only applicationrole/noimportrepair/fallback/
latestsnapshot, sticky503untilrestart proposed. It is NOT SQLvector/candidate retrieval:SQLintegrity
fetchesfullsnapshot andHTTPtiming includesitsnetwork/validation, while coretiming is explicitly separate.

Alternatives:startup-onlycache is cheaper but weakenslivefailuresemantics; header-onlyprobe can miss
childpayload changes; perquerySQL/ANN changes admission/fusion/indexprotocol and is a laterfeature.
Choose fullsmall142snapshot probes for thisproposedcontract, not premature throughputoptimization.
199existingdevcases fixedcomparison/rawbefore-score, no tuning/winner/final105 replay. Proposed
5startup/199pairedHTTP/core after3warmups, nearest-rank ceilings5000/150/250/25ms needownerapproval,
not observedSLA. Legacydev/finaloutputs alreadyviewed; onlynewstorage outputs remain unexecuted.

Trade-offs:readonlyrequestSQL and503latch cost latency/availability; at10×, fullsnapshotvalidation
cost/lock/network/JSONsize must be measured before redesign. Currentrepo142/disposable-name guard
staysunchanged, no synthetic3000claim. Most likely failure is calling storagehydration SQLvectorRAG
or treating human evidence as canonicaltruth. Scope/grounding/auditability PASS for planning;
integrity/safety/cost/extendability runtimeclaims WAIT. See `docs/evidence/t49-3-planning.md`;
owner confirms requirements, then design/tasks/budgets before approvedfreeze/build.

# D50 — Freeze approved inputs separately from unimplemented runtime artifacts

Status:ACCEPTED for HSP-1 input freeze only,2026-09-14. Subsequent three scoped confirmations
accept D49 design/task-budget proposal, but do not certify its runtime behavior or authorize SQL execution.

Copy the approved specification bytes from explicit Git commits with fixed SHA checks, then derive
a new approved storage protocol/declared profile and source-bound manifest via a committed stdlib-only
producer. Leave actual adapter/import manifest and runtime IDs null, and ready_for_real_outputs=false.
Canonical sources, math protocol and old artifacts remain unchanged. New approval record supersedes
historical draft flags; mutable current checklists are not the approved specification authority.

Alternatives: editing every old draft header/flag would obscure exactly what the owner reviewed;
calling an input freeze runtime-ready would invent code/environment evidence; adding database access
here would exceed the first bounded task. Git snapshots and SHA comparison need no new dependencies
or DB credentials. Exclusive publication rejects overwrite and checks reject drift/partial bundles;
it is not crash-atomic or OS-enforced write protection. Most likely failure is confusing a declared
profile with a runnable one; explicit pending bindings/readiness state prevents that claim.

At10×data, hashing all sources grows in cost, but this offline approval gate is not per-request work.
Measure the later fullsnapshot request gate before changing it; do not infer3kthroughput from hashes.
Six-axis scope review:grounding/authority/auditability/local safety PASS; runtime cost/extendability
NOT RUN. Evidence:`docs/evidence/t49-3-input-freeze.md` and its AI rubric;16new/489full tests PASS.

# D51 — Compose a strict storage gate around frozen resolution instead of editing it

Status:ACCEPTED for HSP-2 private/mock implementation,2026-09-14. Use two new modules only. A strict
profile loader verifies explicit mode, complete snapshot/source/protocol/math bindings and runtime
state. A service subclass probes storage then delegates to unchangedResolverService; a new app wrapper
probes health, publishes a separate versioned dependency and latches app unavailable on failure.

This avoids editing source-bound API/service/v4 math and keeps canonical output authority unchanged.
Alternatives rejected:startup-only cache reports success after storage loss; header-only checks miss
child changes; per-query SQL candidates alter RAG mathematics; route/source monkeypatching obscures
the contract; automatic file fallback answers from a source the operator did not select. Full142
reads cost availability/latency but match the approved fail-closed design and will be measured later.

Private profiles require literal mock opt-in and cannot carry runtime images/ready=true. Runtime
profiles require two content-addressed image IDs; HSP-2 publishes only a non-runnable template.
Candidate1 was not overwritten when review found missing health dependency; candidate2 binds the fix
and42 sources at a single commit. Most likely failure is presenting fake-repository behavior as SQL
proof, so HSP-3 remains separately authorized. At10×scale, full snapshot checks may need an immutable
server digest/transaction strategy, but no optimization happens before honest142 cost evidence.

Six-axis:grounding/authority/auditability/mock-integrity PASS; realSQL safety/runtime cost WAIT;
extendability bounded. Evidence:`docs/evidence/t49-3-storage-adapter.md`;55focused/544full PASS.

# D52 — Accept exact file/PostgreSQL parity only from raw-first isolated evidence

Status:ACCEPTED for HSP-3 correctness only,2026-09-15. Owner「繼續執行下一步」after HSP-3 was
named as the next separately authorized action permits new disposable resources, not production,
cost benchmarking or default rollout. Select precommitted profiles/images/source/run settings,
internal-network tmpfs PostgreSQL, an actual SELECT-only role and raw publication before scoring.

The passing run-v4 compares the frozen199 development cases in alternating profile order with fixed
request IDs, top5 output and zero retries/search. SQL performs whole142-snapshot integrity reads,
not TopK/vector retrieval. Candidate mathematics/payload/work and canonical authority remain unchanged.
All failure fixtures and canonical-seven-table hashes are part of the same isolated raw artifact;
cleanup validates exact ownership labels before deletion.

Three earlier infrastructure failures are evidence, not erased attempts:PostgreSQL role DDL rejects
bound password parameters; FK constraints require child-before-header deletion; namespace CHECK
constraints require a controlled drop/restore to exercise application validation. Each correction
received a new source commit and pre-output run freeze. A v1 traceback exposed an already-destroyed
ephemeral credential, so the sensitive raw file was removed and replaced with an explicit sanitized
failure record; later supervisors store only stderr hashes. This narrows auditability slightly for that
failed setup attempt but avoids committing secrets and has no effect on v4 scored output.

Trade-off:full snapshot checks passed correctness but their cost is still unknown. Do not infer HSP-4
latency,3k scalability,durability/concurrency or production readiness from the25.6-second test run.
Grounding/authority/integrity/safety/auditability PASS for HSP-3; cost/10×extendability WAIT.
Evidence:`docs/evidence/t49-3-storage-profile-sql.md`; full suite548PASS.

# D53 — Keep the frozen runtime and replace a missing optional HTTP client with stdlib

Status:ACCEPTED for HSP-4,2026-09-15. The first cost attempt stopped before any timing sample because
the already-frozen runner image did not install`httpx`. Do not download a dependency during the run,
rebuild/select a different image after seeing the failure,or weaken the real-HTTP requirement. Use
Python3's bundled`urllib` for loopback requests,commit that correction,then create a distinct v2
pre-output freeze with the same database/runner image IDs,development pack,measurement boundary and
ceilings. Retain the cleaned v1 failure as evidence.

This choice minimizes changed variables:both clients perform real HTTP against the two single-worker
Uvicorn processes, and the timer still starts before the request and ends after JSON parsing. The
supervisor additionally treats empty/malformed child stdout as a structured runner failure and stores
only stdout/stderr hashes. The trade-off is less convenient HTTP exception handling than`httpx`, but
no network install or new runtime image is needed and the cost run remains reproducible.

Run-v2 raw SHA`78e9eb…7ed` preceded evaluation SHA`af5ff0…cccc`; all eight frozen p95 gates pass with
no timed retries,threshold changes or cleanup residue. This accepts the local142/concurrency1 cost of
full-snapshot checks and completes boundedT49.3. It does not approve T49.4 packaging/default rollout,
production SLA,throughput/durability,real3k scaling or release-variant attributes. Evidence:
`docs/evidence/t49-3-storage-profile-cost.md`; focused79/full552 tests PASS.

# D54 — Add a dedicated opt-in image instead of rewriting historical packaging

Status:ACCEPTED for bounded T49.4,2026-09-15. Preserve the original`Dockerfile`,`.dockerignore` and
`docker-compose.yml` byte-for-byte because their hashes are part of the passed IBR-T5 runtime record.
Package the optional file-backed storage app through separately named Dockerfile,ignore and Compose
files,with an explicit`human-storage` profile and an external read-only profile bound to the exact
image ID. This keeps`docker compose up api` and canonical authority unchanged while making the
already-tested human gate operable on demand.

An initial direct edit of the old packaging files was reversed when the frozen IBR-T5 regression test
correctly detected SHA drift. The first dedicated image then failed strict startup because the runtime
allowlist contained all direct profile inputs but omitted a selection file and producer reached through
the v4 math protocol. Do not weaken recursive verification or include all reports. Instead, enumerate
the exact transitive evidence,create a new image and exclusive v2 freeze,and retain the sanitized v1
failure. This gives a smaller and auditable context at the cost of maintaining an explicit allowlist.

The passing v2 run uses image`sha256:d8ccf54d…0e718`,profile SHA`a51d3112…980a` and raw report
SHA`bac44242…761c`. It proves local ARM64/file-mode packaging,one worker,loopback transport,nonroot,
read-only runtime,missing-profile rejection,four unchanged canonical responses and exact cleanup.
It does not install PostgreSQL:that would require persistent naming,secret,migration/import and volume
lifecycle decisions that the current disposable-name guard deliberately rejects. At10× scale,the
current full-snapshot request gate still requires new measurement before redesign or rollout.

Six-axis result:grounding,authority,integrity,local safety and auditability PASS; extendability is
BOUNDED to142 documents/file mode/concurrency1. Evidence:
`docs/evidence/t49-4-human-storage-runtime-package.md`; full559/focused71 tests PASS.

# D55 — Treat every release row as an observation before treating any pair as a variant

Status:ACCEPTED for VAR-PLAN1 offline planning,2026-09-15. Join the frozen normalized/review/final
queue by exact source-record ID,then assign a separate deterministic observation ID. Preserve the
family decision as casting context only;leave variant-equivalence ID,canonical UUID and owner field
decision null. Every physical field keeps its own raw value,state and evidence pointer. Null means
unknown,not equality;`2nd Color`,`3rd Color`and`Zamac`remain literal notes rather than inferred colors.

Alternatives rejected:a spreadsheet with one row and a single confidence hides which field is sourced;
grouping by casting+null attributes would merge unknowns;using toy number as identity confuses source
references with product truth;fetching pages now would cross the unresolved rights gate. A deterministic
JSON envelope plus readable Markdown is more verbose,but it can later become append-only review/database
records without rewriting what was originally observed.

Choose the first workload by greedy new-pattern coverage over complete families,cap5families/15rows,
and stop when no new pattern remains. This produces4families/11rows covering create/merge/hold,
2nd/3rd Color,Zamac,series divergence,three-row families and repeated rows without notes. It is an
educational risk batch,not a random sample or quality estimate. An initial uncommitted selector compared
mutable dictionaries and repeated a family;stable family IDs and a uniqueness test replace that choice.

At10×,100 full JSON evidence envelopes suggest pagination/storage may eventually help,but no database
is selected before humans validate the workflow. The most likely failure is promoting a family decision
into release truth. Grounding,authority,integrity,safety and auditability PASS for the plan;
extendability BOUNDED and variant quality/source permission NOT EVALUATED. Evidence:
`docs/evidence/var-plan1-release-field-evidence-review.md`;9focused/568full tests PASS.

# D56 — Freeze a question packet before recording owner release decisions

Status:ACCEPTED for VAR-REVIEW1-PREP only,2026-09-15. Present the exact4family/11row VAR-PLAN1 batch
beside already-frozen research,then generate a separate all-null decision template bound to the packet
SHA. Earlier family approvals remain casting-only. A secondary claim becomes a row-level candidate only
when its frozen observed text explicitly names that toy number;URL slugs,series labels and family-level
variant overlap cannot add physical fields.

This rule produces exactly three candidate claims:HYW93 Lamborghini release,JBC35 Audi Super Treasure
Hunt,and HYX54 Nissan Tooned lineage. It deliberately does not map Subaru's family-level Zamac evidence
to HYY12,and it rejects a color hinted only by Nissan's URL. Alternatives—prefilling “obvious” choices,
using variant-note order as distinct identity,or asking only one family-level question—would make review
faster but would hide the evidence gap and collapse source observation into release truth.

Every one of143 field slots and10 pairwise relationships starts null. A completed event must name the
reviewer,time,reason,evidence and exact packet SHA;unknown/conflicted remains valid. The extra packet/
template/manifest files cost repetition,but let a reviewer distinguish what the machine assembled from
what the owner authorized. At10×,a review UI may be needed;this Markdown batch does not measure that.

Most likely failure is interpreting a familiar marketing phrase or URL as an approved color/edition.
Grounding,authority,integrity,safety and auditability PASS for preparation;human correctness,source
permission and scale are NOT EVALUATED. Evidence:`docs/evidence/var-review1-batch-01-preparation.md`;
11focused/579full tests PASS.

# D57 — Interpret continuation only within the immediately preceding owner question

Status:ACCEPTED for VAR-REVIEW1 decision01,2026-09-15. The owner replied`繼續下一步`directly after the
question asking whether to accept the stated Lamborghini conservative result. Record approval only for
that exact result:confirm HYW93 casting/toy/year;keep five physical fields unknown on each of three rows;
mark its three row pairs different releases. Do not infer approval for Subaru,Nissan,Audi,unmentioned
source fields,new access or canonical promotion.

Alternatives:requiring the owner to repeat the full recommendation would be less ambiguous but adds
friction after a direct scoped question;interpreting“continue”as the entire batch would exceed authority.
The event therefore stores verbatim question,response,interpretation and recording time,and a validator
requires every field/pair in this conservative scope. The remaining source-observed fields stay
unconfirmed rather than silently accepted.

This completes1/4 owner families,not VAR-REVIEW1. At10×,event sequence/version rules need automation,
but scoped append-only records already prevent later conversations from overwriting earlier evidence.
Most likely failure is scope creep from a short affirmative reply. Grounding/authority/integrity/safety/
auditability PASS;extendability bounded. Evidence:`docs/evidence/var-review1-decision-01-lamborghini.md`;
10focused/589full tests PASS.

# D58 — Confirm literal variant notes without promoting their implied physical attribute

Status:ACCEPTED for VAR-REVIEW1 decision02,2026-09-15. The owner answered`是`to the scoped Subaru
proposal. Confirm exactly HYY12's frozen`2nd Color - Zamac`variant-note text,mark HYW99/HYY12/JBB55
as different releases,and keep all15 physical fields unknown. Do not translate Zamac into body color,
join HYY12 to the older human Walmart Exclusive variant,or approve Nissan/Audi/canonical/source work.

The validator accepts additional reviewed fields only when explicitly declared and present in the
same packet row;confirmed value must still equal frozen evidence. This is preferable to either ignoring
the owner's source-text confirmation or treating a meaningful token as all the physical facts it may
suggest. The trade-off is two layers—literal note confirmed,physical field unknown—but that difference
is the core provenance boundary.

Batch progress is2/4. Most likely failure remains collapsing family-level Zamac overlap into row-level
identity. Six-axis grounding/authority/integrity/safety/auditability PASS,extendability bounded.
Evidence:`docs/evidence/var-review1-decision-02-subaru-brz.md`;13focused/592full tests PASS.

# D59 — Keep tool-lineage confirmation separate from homonymous family identity and URL color

Status:ACCEPTED for VAR-REVIEW1 decision03,2026-09-16. The owner replied`繼好下一步`to the scoped
Nissan proposal. Treat the apparent typo as continuation of the immediately preceding explicit question,
but preserve the verbatim response and narrow its authority to Nissan only. Confirm HYX54's five frozen
candidate fields:casting name,toy number,2025,HW J-Imports,and`tool_lineage_ref = Tooned`. Mark
HYW79/HYY30/HYX54 as different releases and keep all15 physical fields unknown.

The independent source URL contains`metalflake-blue`,but the frozen observed claim does not state color;
the event therefore records null color rather than deriving a fact from routing text. A separate non-Tooned
tool shares the display name,so one row's Tooned lineage does not authorize creation or merge of the whole
family. This preserves three distinct layers:source row,tool lineage,and canonical family identity.

Alternatives were to infer blue from the URL,apply Tooned to every same-name row,or leave the five explicit
candidate fields pending. The first two overstate evidence;the last discards the owner's scoped confirmation.
The chosen event confirms only attributable values while retaining the family hold. Batch progress is3/4.
Most likely failure is treating display-name equality as tool identity. Grounding/authority/integrity/safety/
auditability PASS;extendability bounded. Evidence:
`docs/evidence/var-review1-decision-03-nissan-skyline-2000gt-r-lbwk.md`;16focused/595full tests PASS.

# D60 — Close owner review without promoting reviewed observations

Status:ACCEPTED for VAR-REVIEW1 decision04 and batch01 closure,2026-09-16. The owner replied
`繼續下一步`to the scoped Audi proposal. Confirm only JBC35's four frozen candidate fields:casting name,
toy number,2025,and`edition = Super Treasure Hunt`. Keep all five HYW72 physical fields and JBC35's
color,wheel,tampo,packaging unknown;mark the two rows different releases. Do not transfer JBC35's edition
to HYW72 or infer any visual details from the marketing class.

Four family events now exhaust the exact batch01 review scope:67 required field decisions are13 confirmed
and54 unknown;all10 pairs are different releases;canonical changes remain0. Mark VAR-REVIEW1 complete,
but do not change the frozen packet's held rows,write canonical IDs,alter runtime/PostgreSQL,or treat reviewed
source observations as promoted products. Review completion and catalog publication are separate gates.

The alternative was to auto-promote rows once all questions were answered,which would collapse human
review into canonical authority and bypass unresolved physical evidence. The chosen closure preserves a
clean handoff to VAR-PLAN2,where source rights,page revisions and request budgets must be approved before
new collection. Most likely failure is reporting4/4 as11 fully verified variants. Grounding/authority/
integrity/safety/auditability PASS;extendability bounded. Evidence:
`docs/evidence/var-review1-decision-04-87-audi-quattro.md`;20focused/599full tests PASS.

# D61 — Treat content licensing and automated source access as separate gates

Status:ACCEPTED for VAR-PLAN2-DRAFT,2026-09-16. Fandom's general licensing page says wiki text is
usually CC BY-SA3.0 with attribution/share-alike,but its Terms of Use,last revised2025-12-19 in public
search metadata,prohibit automated access/scraping without express prior written permission. The project
has no permission artifact and could not directly verify the Hot Wheels Wiki-specific license,API endpoint
or robots state. Therefore collection remains disabled;CC BY-SA context is not bot permission.

Freeze a planning-only JSON gate with zero executed/current requests,no approved endpoints,no images/OCR,
no SQL/canonical changes and100/500/1,500/3,000 honest counters. A later permission artifact does not start
collection:it must be checked for scope/expiry/endpoints,followed by authorized community license/robots
verification and a new owner approval for at most three serial,cached,contact-identified GET requests.
MediaWiki etiquette is a conditional transport floor,not Fandom authority.

Alternatives were immediate scraping,assuming public pages imply permission,or abandoning the source goal.
The first two conflict with current terms;the last discards a potentially viable path before requesting
permission. The chosen plan is slower but prevents an interview project from demonstrating noncompliant data
acquisition. At10×,source rights remain the throughput bottleneck,not PostgreSQL. Most likely failure is
reporting general license text as automated-access consent. Six-axis grounding/authority/integrity/safety/
auditability PASS;extendability bounded. Evidence:`docs/evidence/var-plan2-source-expansion-draft.md`;
11focused/610full tests PASS.

# D62 — Import owner-supplied release workbooks into isolated deterministic staging

Status:ACCEPTED for LRS-T1–T4,2026-09-16. The owner explicitly asked to expand the database from four
local 2023–2026 workbooks while deferring color. Treat the 1,763 rows as source observations only:
normalize them offline, preserve their provenance, and write them to new`release_source_batch`and
`release_source_record`tables. Do not insert them into canonical product/alias/identifier/search/
embedding tables,`hk_*`,evaluation labels or either Dual RAG corpus.

Choose`openpyxl`because XLSX is a zipped workbook format with worksheet types,formula cells and sparse
dimensions that a CSV parser cannot validate honestly. Read-only/data-only passes keep memory bounded and
separate formula rejection from value parsing. The alternative—manual export to CSV or a heavier dataframe
stack—would either lose workbook structure/provenance or add machinery without solving the strict sheet/header
contract. A fixed19-column schema, exact filenames/years/counts and per-file SHA-256 fail closed when an input
is replaced. QA exposed one real weakness:the first scanner stopped at column19 and silently accepted populated
column20. The task returned to Phase2; scanning the full populated row plus two regressions closed the gap before
the final owner-data run passed19 focused tests and629 full tests.

Build a deterministic normalized snapshot before SQL so the same four bytes produce the same ordering,payload,
content checksum and batch ID. The complete normalized snapshot remains local with the unpublished XLSX files.
`/HW data/`and its generated bundle are gitignored because local possession does not establish redistribution
rights;omitting all evidence would make the import unauditable,while committing source rows would overstate
publication authority. The public repo therefore keeps only an aggregate manifest/report with filenames,
checksums,counts and the missing-rights state,not the1,763 source rows.

Portability follow-up,2026-09-17:because gitignored owner files will not exist in a public clone,keep exact owner-byte checks as two explicit
integration tests but generate exact-shape synthetic workbooks for the17 portable parser/repository tests. A
fresh-clone simulation therefore returns17 PASS/2 SKIP instead of failing at collection,while local owner data
returns19/19. The alternative—committing XLSX to make tests convenient—crosses the rights boundary; skipping all
workbook tests loses contract coverage. Synthetic fixtures preserve schema/count/tamper behavior,while the
committed aggregate manifest checks batch identity,source checksums and the1,763-row output claim. Production path validation is unchanged and
still refuses any source outside the four direct`HW data/`files.

Keep blank color as SQL`NULL`. Variant notes such as`2nd Color`,`3rd Color`or`Zamac`,URLs and general knowledge
cannot supply the physical color of a particular source row. Inferring them would increase apparent completeness
while corrupting provenance. Deferring color leaves1,763 unknowns but permits later evidence-backed enrichment
without retracting fabricated facts.

Use one PostgreSQL transaction for the batch and all records,table locking plus unique identities for races,
and exact readback verification before commit. An identical batch returns`unchanged`; an existing deterministic
batch ID with another checksum is a collision and fails,as do invalid/duplicate records,with full rollback. The
alternative upsert-by-row could hide changed evidence and leave a partially imported batch. Two isolated tables
cost an eventual promotion step,but make the authority boundary visible in schema and permit safe deletion or
reprocessing without touching resolver truth.

Disposable QA applied/downgraded/reapplied migration`0003`,proved real uniqueness rollback,then imported and
read back1,763 rows;that database/container was removed. The separate retained local project volume subsequently
returned`inserted`then`unchanged`and contains1 batch/1,763 rows/1,763 unique source IDs/1,763 unique toy numbers/
678 castings/1,763 null colors/0 canonical links,with years445/441/440/437. These results prove ingestion
mechanics,not source correctness,rights,variant review or resolver accuracy. Architect/security/performance
reviews remain deferred under Lite mode;3,000-row latency,backup/restore,promotion rules and color enrichment
require later evidence. Evidence:`docs/evidence/local-release-staging-ingestion.md`.

# D63 — Treat normalized casting matches as private review routing, not identity approval

Status:ACCEPTED for LCR-T1–T3,2026-09-17. After isolated staging, group the1,763 observations by
NFKD/ASCII/casefold/alphanumeric brand-and-casting keys to make human review tractable. Preserve all raw
labels and row references in a private queue, call the result a review cluster, and flag any normalized
key that contains multiple source spellings. The current data therefore has678 raw labels but676 clusters,
including2 explicit normalization collisions;normalization is not silently promoted to alias truth.

Compare only exact normalized keys against the synthetic canonical fixture and non-canonical human draft.
This yields1 both-source,2 fixture-only,40 human-only and633 no-exact clusters,covering1/8/126/1,628
observations. Keep all676 unresolved with0 approved links,0 canonical promotions and0 reviewed colors.
Fuzzy nearest-neighbour matching was rejected for this gate because it can make a review queue look complete
by manufacturing false identities;automatic exact linking was also rejected because the fixture is synthetic,
the human catalog is a draft,and neither proves a release-level variant.

The complete queue is gitignored because it reproduces owner-supplied labels and row references without a
republication-rights artifact. Commit only aggregate counts,input hashes and the private queue checksum. This
retains auditability without publishing1,763 derived rows. At10×,manual review throughput—not candidate
generation—is the bottleneck;the next design should use small append-only owner decision batches. Most likely
failure is reporting43 exact candidates as43 verified families. Grounding/authority/integrity/safety/privacy/
auditability PASS for review support;runtime and promotion eligibility remain blocked. Evidence:
`docs/evidence/local-release-casting-review.md`;11 focused/640 full tests PASS.

# D64 — Freeze a five-question owner packet before recording any casting decision

Status:ACCEPTED for LCB-T1–T3,2026-09-17. Select exactly five high-priority review clusters from the
verified private queue:one cross-source exact candidate,two normalization collisions,and two synthetic-
fixture-name candidates. This bounded batch covers18 observations and is large enough to exercise the three
decision shapes without asking the owner to review676 clusters at once.

Freeze the evidence before answers. Each item carries attributable source fields and exact candidate summaries,
but its decision remains null and pending. Allowed responses are`same_review_family`,`keep_separate`,or`unknown`;
the first records only a review-level relationship and cannot approve a release variant,color,synthetic fixture
product or canonical UUID. The alternative—prefilling the obvious-looking exact/collision cases—would turn a
question-generation step into unrecorded identity authority.

Keep the complete packet local/gitignored because it contains owner-derived labels,toy numbers and row evidence.
Commit only hashes and aggregate selection counts. Packet preparation changes no SQL,catalog,API,evaluation or
Dual RAG state. At10×,fixed small batches need an append-only decision-event registry and progress counters,but
batch01 intentionally stops before that mutation. Most likely failure is interpreting packet QA PASS as owner
approval. Grounding/integrity/safety/privacy/auditability PASS;authority remains pending owner answers. Evidence:
`docs/evidence/local-release-casting-review-batch-01.md`;9 focused/649 full tests PASS.

# D65 — Record each owner answer as an ordered packet-bound event

Status:ACCEPTED for local casting decision01,2026-09-17. The owner answered the first frozen question with
the exact backtick-delimited value`same_review_family`. Preserve that response privately,normalize it only
after verifying the allowed value,and bind the event to packet SHA,packet batch,question ordinal and review
cluster. Its only authorized effect is one review-level family relationship.

Do not update the original packet or overwrite a cumulative answer object. Use a contiguous append-only event
ledger so later answers retain the checksum and bytes of every earlier event;reject duplicates,gaps,stale packet
references,response/decision disagreement and checksum/summary tampering. The alternative mutable template is
simpler,but cannot prove that question1 remained unchanged after question5.

Keep the verbatim answer and question identity private;publish only hashes and aggregate1/5 progress. Exclude
release-variant approval,color inference,synthetic-product selection,canonical UUID,SQL,evaluation and Dual RAG
effects. Most likely failure is treating`same_review_family`as same release or applying it to questions2–5.
Grounding/authority/scope/integrity/privacy/non-generalization PASS. Evidence:
`docs/evidence/local-release-casting-decision-01.md`;9 focused/658 full tests PASS.

# D66 — Treat an owner-supplied numeric prefix as a checked question reference

Status:ACCEPTED for local casting decision02,2026-09-17. The owner's second answer includes both an
ordinal and an allowed decision. Preserve the complete response in the private event,but remove the
optional `<number>.` prefix only after proving that it equals the event's question ordinal. A wrong
prefix fails before any file is replaced. This makes the owner's `2.` useful evidence instead of
silently discarding it as formatting.

Blindly stripping every numeric prefix was rejected because an answer intended for question3 could
then be recorded as question2. Rejecting every prefixed answer was also rejected because the user
explicitly supplied a clear,matching ordinal and preserving it strengthens auditability. Responses
without a prefix remain valid for compatibility with event1; both forms must normalize exactly to
one frozen allowed decision.

Record question2 as another `same_review_family` review relationship and retain event1 unchanged.
Do not merge the six release observations or infer color from `2nd Color`,year,series,URLs,or names.
Publish only cumulative hashes and aggregate2/5 progress. Canonical UUID,SQL,evaluation and Dual RAG
effects remain zero. Most likely failure is treating the family decision as one physical variant;
grounding/authority/scope/integrity/privacy/non-generalization PASS. Evidence:
`docs/evidence/local-release-casting-decision-02.md`;11 focused/660 full tests PASS.

# D67 — Bind an unprefixed owner answer through contiguous ledger order

Status:ACCEPTED for local casting decision03,2026-09-17. The owner's third response is the exact
allowed value`same_review_family`without a numeric prefix. Accept it only through the existing
append contract:two valid prior events make question3 the sole writable ordinal. Bind it to the
frozen packet and private cluster,append event3,and retain events1–2 unchanged.

Requiring the user to repeat a numeric prefix was rejected because the ledger already has a stronger
machine-checked sequence invariant;inferring question3 from the content alone was also rejected.
The identity comes from the recorder's explicit ordinal plus contiguous event count,while the exact
response proves the chosen decision. Duplicate or skipped ordinals continue to fail closed.

Confirm only the review-family relationship for the source observations. Do not merge the releases,
infer color,select a synthetic product,create a canonical UUID,write SQL,or alter
evaluation and Dual RAG. Publish only hashes and aggregate3/5 progress. Most likely failure is
generalizing three consecutive equal answers to questions4–5;grounding/authority/scope/integrity/
privacy/non-generalization PASS. Evidence:`docs/evidence/local-release-casting-decision-03.md`;
11 focused/660 full tests PASS.

# D68 — Reuse the ordered decision contract for the fourth owner answer

Status:ACCEPTED for local casting decision04,2026-09-18. The owner's fourth response is the exact
allowed value`same_review_family`without a numeric prefix. Record it through the same packet-bound,
contiguous ledger used by decision03:three valid prior events make question4 the sole writable
ordinal,and all earlier event bytes/checksums must remain unchanged.

Do not add question-specific product code merely because another owner answer arrived. The generic
recorder already distinguishes the explicit ordinal,verbatim response,normalized decision and narrow
authorized effect. Reusing it keeps the workflow deterministic and avoids five nearly identical
recording paths that could drift in validation or privacy behavior.

The decision confirms only one review-family relationship for the private fixture-name candidate.
It does not merge release observations,infer color,select the similarly named synthetic fixture,
create a canonical UUID,write SQL,or alter evaluation and Dual RAG. Publish only hashes and aggregate
4/5 progress. Most likely failure is assuming the fourth identical answer also settles question5;
grounding/authority/scope/integrity/privacy/non-generalization PASS. Evidence:
`docs/evidence/local-release-casting-decision-04.md`;11 focused/660 full tests PASS.

# D69 — Close the owner packet without materializing its family decisions

Status:ACCEPTED for local casting decision05,2026-09-18. Append the fifth exact owner response through
the same contiguous,packet-bound ledger. Four valid prior events make question5 the only writable
ordinal;after it is validated,the ledger status deterministically changes from
`in_progress_awaiting_owner`to`complete`and pending count becomes zero.

Define completion narrowly. It proves that every frozen question has one attributable answer;it
does not mean those review-family relationships exist in the canonical catalog,PostgreSQL resolver
tables,evaluation labels,or either Dual RAG corpus. Automatic materialization was rejected because
the five decisions do not choose canonical UUIDs,release variants,physical colors,or a rollback and
conflict policy.

Keep the complete ledger private and publish only hashes plus aggregate5/5 closure. The next feature
must specify an auditable materialization artifact and preserve the distinction between family
relationship and release variant. Most likely failure is presenting`complete`as full product-data
resolution;grounding/authority/scope/integrity/privacy/non-generalization PASS. Evidence:
`docs/evidence/local-release-casting-decision-05-closure.md`;11 focused/660 full tests PASS.

# D70 — Materialize local owner decisions as a separate review-layer registry

Status:ACCEPTED for LRFM-T1–T4,2026-09-18. Transform the complete five-event local decision ledger
into a dataset-specific private registry with five deterministic review relationship IDs and18 held
source references. Do not reuse the earlier 2025 Wiki registry:its lineage,decision semantics and
source authority differ from the owner-supplied 2023–2026 release staging chain.

Use SHA-derived relationship IDs rather than canonical UUIDs. Preserve private labels and source
references for audit,but represent candidate evidence only by checksum and
`context_only_not_selected`;an affirmative review-family answer does not select a synthetic fixture
or human-draft target. Non-affirmative decisions are supported as explicit exclusions rather than
being silently dropped.

Publish as an immutable pair:the first build creates private/public directories,an exact rerun is
unchanged,and partial or conflicting outputs fail without overwrite. Roll back directories created
by a failed first attempt. Keep the registry gitignored and commit only aggregate hashes/counts.
At10×,batch partitioning and registry composition will need explicit collision rules;the most likely
failure is treating a review relationship as canonical or release-level identity. Grounding/
authority/scope/integrity/privacy/non-generalization PASS. Evidence:
`docs/evidence/local-release-casting-review-family-materialization.md`;13 focused/673 full tests PASS.

# D71 — Prepare a private local family corpus before changing Dual RAG runtime

Status:ACCEPTED for LRFK-T1–T4,2026-09-19. Derive five typed`review_family`documents from the private
local registry,but mark them eligible only for offline retrieval evaluation. Preserve their distinct
lineage instead of appending them directly to the existing42-document 2025 Wiki projection or
changing the API/runtime loader in the same feature.

Allow only brand,casting and owner-confirmed observed aliases as future searchable text. Keep source
IDs as private provenance and omit toy numbers,years,series,variant notes,candidate evidence,color
and release attributes from the search surface. Generate namespace UUIDv5 keys for typed retrieval;
they are review knowledge keys,not canonical product UUIDs.

Before publication,compare IDs,UUIDs and normalized brand-plus-casting/alias identities against the
existing42-family corpus and fail on any collision. Real inputs produce5 documents/18 references/
0 collisions. Keep full documents gitignored;commit only hashes,allowlists and aggregate counts.
At10×,collision policy and independent noisy-query evaluation become the bottleneck. Most likely
failure is treating exact-name wiring as retrieval quality or silently indexing the private corpus.
Grounding/authority/scope/integrity/privacy/non-generalization PASS. Evidence:
`docs/evidence/local-release-review-family-knowledge.md`;13 focused/686 full tests PASS.
