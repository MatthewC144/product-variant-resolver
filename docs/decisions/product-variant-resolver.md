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
