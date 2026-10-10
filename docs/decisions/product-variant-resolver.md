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

# D72 — Preserve local shadow-retrieval FAIL and block runtime integration

Status:ACCEPTED for LRFE-T1–T4,2026-09-19. Freeze15 non-exact positive questions and5
near-confusable hard negatives against the five private local-family documents before retrieval.
Run them as shadow candidates beside the current142-document Human Knowledge corpus with the
already selected v4 configuration. Publish raw candidates before opening the separate expected-label
file;never retry or rewrite a case after output is visible.

Precommit gates of positive Recall@5=1.0,Recall@1>=0.8,family coverage@5=1.0,zero forbidden-family
hard-negative hits and zero retrieval errors. The first three quality metrics pass at15/15,13/15 and
5/5,and errors are zero,but forbidden hits equal3. Preserve overall FAIL rather than lowering the
threshold,removing difficult negatives or tuning on this20-case test set.

Keep queries,labels,candidates,ranks and case results private;commit only hashes,configuration,
aggregate metrics,gates and zero downstream effects. The five documents remain offline-evaluation
candidates only. Most likely failure is broad admission from shared manufacturer,numeric model or
generic body-style terms. A future mitigation needs separate development data and a new spec;this
immutable test result cannot become its tuning set. Grounding/authority/scope/integrity/privacy/
non-generalization PASS for evidence handling but retrieval-quality gate FAIL. Evidence:
`docs/evidence/local-release-review-family-retrieval-evaluation.md`;13 focused/699 full tests PASS.

# D73 — Build a separate false-positive development set before mitigation

Status:ACCEPTED for HKFP-T1–T4,2026-09-20. Do not tune against the failed private20-case local
evaluation. Instead,manually freeze24 required-plus-forbidden pairs using only the committed
142-document Human Knowledge corpus. Require each pair to share an identity-core token,remain
different typed knowledge documents,and use a contextual query unequal to either identity.

Record the unchanged v4 floor0.5/weight1.0/hashing192 Top-5 baseline without adding an admission
rule or declaring PASS. Required targets rank first in24/24,but forbidden neighbors also appear in
18/24,safety accuracy0.25. This confirms a broad-admission problem on a larger development surface
while preserving required retrieval.

Commit the public pack,source hashes,raw ranks and aggregate report because all inputs already belong
to the repository;do not read private local artifacts. A future grid may tune on this dev pack and
the existing199 positive dev cases,but final/private evidence remains excluded until a policy is
frozen. Most likely failure is improving safety by deleting valid typo/abbreviation candidates;
selection must gate both recall and forbidden admission. Grounding/scope/integrity/auditability/
non-leakage PASS;retrieval safety remains diagnostic only. Evidence:
`docs/evidence/human-knowledge-false-positive-development-v1.md`;12 focused/711 full tests PASS.

# D74 — Reject global hard coverage filtering as the mitigation

Status:ACCEPTED for HKAD-T1–T4,2026-09-20. Freeze five identity-token coverage thresholds and score
them from one223-query retrieval collection across the199 existing and24 safety development cases.
Require exact preservation of168 positives,4 merges,0 governance violations,0 unrelated results,
24 new required hits and0 errors before considering false-positive reduction.

Nonzero filters reduce forbidden cases from18 to7/2/0/0,but respectively retain only167/165/159/152
old positives;the two strictest also retain23/22 new required targets. Therefore every attempted
mitigation fails at least one frozen recall gate. The deterministic ordering returns baseline as the
only eligible configuration,but baseline is a fallback—not evidence that the problem is solved.

Do not lower the recall gates after seeing output,activate the baseline as a new policy,or consult the
private20-case test. Preserve v1 as a failed design alternative and move to a v2 candidate-relative
penalty/reranker that can distinguish unmatched model tokens from legitimate typo/abbreviation forms.
Most likely failure remains trading false positives for silent false negatives. Integrity/scope/
auditability/non-leakage PASS;mitigation effectiveness FAIL. Evidence:
`docs/evidence/human-knowledge-admission-development-v1.md`;15 focused/726 full tests PASS.

# D75 — Reject candidate-relative reranking without an admission decision

Status:ACCEPTED for HKRR-T1–T4,2026-09-20. Freeze a wider Top-25 collection and seven weights before
measurement,then score every candidate as original RRF divided by a candidate-relative unmatched
identity-token penalty. Reuse the same223 public-development pools across all settings and preserve
the existing recall/governance gates;do not read the private20-case evaluation.

All seven settings preserve168/168 old positives,24/24 new required targets,4/4 merge controls and
zero existing governance violations,but all leave18/24 forbidden cases in Top5. Only5 of223 pools
contain more than five candidates;the safety subset median is3 and only2/24 exceed5. Reordering can
change rank but cannot remove a wrong candidate when the entire available pool fits inside Top5.

Treat baseline as a deterministic fallback,not a selected mitigation. Do not enlarge weights after
observing this result or activate v2. The next design must combine ranking with an explicit
query-candidate admission/abstention decision while protecting the three old positives not currently
at rank1. Most likely failure is solving false positives by silently returning only the first result.
Integrity/scope/auditability/non-leakage PASS;mitigation effectiveness FAIL. Evidence:
`docs/evidence/human-knowledge-reranker-development-v2.md`;13 focused/739 full tests PASS.

# D76 — Select a rank-1 anchor plus 0.75 secondary compatibility gate for private validation

Status:ACCEPTED for HKAA-T1–T4,2026-09-20. Bind admission v3 to the immutable public v2 raw report
and execute zero new retrieval calls. Always retain source rank1;for ranks2–5,admit only candidates
whose frozen identity-token coverage meets the configured threshold. Preserve source order and never
promote candidates beyond the original Top5.

Across eight precommitted thresholds,0.75 is the lowest eligible setting with zero forbidden cases.
It preserves168/168 existing positives,24/24 new required targets,4/4 merges and zero governance
violations/errors while reducing forbidden hits from18/24 to0/24. Threshold1.0 also reaches zero but
loses one old positive and is rejected. The selected policy admits212/329 source candidates and
abstains from117 secondaries.

Authorize only a new versioned private shadow evaluation. Do not overwrite or tune against the old
20-case FAIL and do not activate API/runtime. The most likely failure is an unseen wrong rank1,
because the anchor is intentionally exempt from secondary filtering;the new private gate must report
that behavior explicitly. Grounding/scope/integrity/auditability/non-leakage PASS;generalization is
unproven. Evidence:`docs/evidence/human-knowledge-anchor-admission-development-v3.md`;12 focused/
751 full tests PASS.

# D77 — Preserve private anchor-evaluation FAIL and block runtime integration

Status:ACCEPTED for LRAE-T1–T4,2026-09-21. Bind the exact public`secondary-075`winner to all immutable
v1 private evidence hashes before scoring. Reuse the original20 raw Top-5 rows,compute identity
coverage offline,and execute zero retrieval calls. Write a separate ignored v2 private result and
publish only aggregate hashes,metrics,gates,policy and zero downstream effects.

The policy preserves15/15 positive hits,13/15 rank1 positives,5/5 family coverage and zero errors.
It reduces forbidden hits from3 to2 by removing one secondary false positive,but both survivors are
source rank1. Therefore the zero-forbidden and zero-forbidden-rank1 gates fail. Preserve FAIL;do not
raise0.75,rewrite the anchor,rerun retrieval or create case-specific exceptions after seeing output.

Return to public development to design rank1 compatibility/confidence evidence that also protects
valid low-coverage typo anchors. The private failures remain test evidence and cannot become tuning
labels. Runtime/API/PostgreSQL/canonical/release/color integration stays blocked. Most likely failure
is overcorrecting by rejecting valid rank1 typo matches. Integrity/privacy/auditability PASS;
generalization and safety FAIL. Evidence:`docs/evidence/local-release-review-family-anchor-admission-evaluation-v2.md`;
10 focused/761 full tests PASS.

# D78 — Reject scalar rank-1 anchor confidence and keep runtime blocked

Status:ACCEPTED for HKAC-T1–T4,2026-09-21. Build a public-only development pack before retrieval:
ten valid low-coverage rank1 anchors plus twelve casting identities absent from the committed
142-document corpus. Freeze the formula`max(identity_token_coverage,bounded_character_score)`,the
0.75 secondary gate,ten rank1 thresholds,source hashes and exact recall/safety gates. Retrieve the
22 new queries once and reuse those raw rows for every configuration while re-scoring the existing
223 public rows. Do not read private evaluation artifacts.

No configuration is eligible. Threshold0.61 preserves168/168 existing positives and10/10 anchor
positives but leaves10/12 missing identities nonempty. Threshold0.625 still leaves10/12 nonempty and
already falls to167/168 plus9/10. Threshold0.75 leaves4/12 nonempty while retaining only167/168 and
9/10. The two public signals therefore overlap across valid typo anchors and plausible wrong-family
neighbors; another scalar cutoff cannot meet both frozen gates.

Preserve the null winner and do not start another private evaluation,activate API/runtime,or invent
case-specific exceptions. The next development design must add new public candidate-specific
contradiction or identity-span evidence and freeze it before retrieval. Integrity,privacy,
auditability and regression behavior PASS;promotion safety FAIL. Evidence:
`docs/evidence/human-knowledge-anchor-confidence-development-v4.md`;9 focused/770 full tests PASS.

# D79 — Develop bilateral identity contradiction before another private evaluation

Status:ACCEPTED for HIC planning,2026-09-21. Replace scalar rank1 confidence development with an
auditable candidate-specific question:after selecting the best query identity span and aligning it
to casting/approved aliases,do both sides retain incompatible model evidence?Use ordered one-to-one
alignment,public-corpus IDF residual weights and an explicit same-frame numeric conflict. Preserve
the existing0.75 secondary gate and source order.

Build a new public24-case pack before retrieval:12 correct rank1 preservation cases not used by v4
and12 new corpus-absent contradiction cases. Freeze seven policies and exact old/v4/new gates,then
retrieve each new query once into a label-blind raw artifact before scoring. Do not use private
failures,series,color,release metadata,IDs or case exceptions.

This choice has a 10x auditability advantage over a neural cross-encoder:every decision identifies
the aligned span,residual atoms,numeric state and reason code,and the full experiment remains local
and deterministic. The trade-off is less semantic flexibility. The most likely failure is rejecting
a legitimate shorthand with bilateral residuals,or accepting a nonnumeric model substitution hidden
by compact similarity. Exact positive and negative gates test both. Requirements,design and tasks
were confirmed sequentially;implementation begins with an unfrozen pack constructor only.

# D80 — Reject identity-contradiction v1 for promotion and preserve the null winner

Status:ACCEPTED,2026-09-21. The v1 experiment is valid but no policy is eligible. Baseline preserves
168/168 existing,10/10 v4 and12/12 new positives,but leaves11/12 v4 and10/12 new absent identities
nonempty. The strict `contradiction-050` reduces both negative sets to1/12,but recall falls to164/168,
9/10 and11/12. Thresholds1.00–1.50 preserve the two new positive sets but lose one existing positive
and still leave five to seven negative cases nonempty.

Keep `winner:null`;do not authorize private evaluation,API/Dual RAG runtime,PostgreSQL,canonical or
variant behavior. Implementation quality,privacy,integrity,auditability and reproducibility PASS;
positive-preservation and absent-identity safety cannot pass simultaneously,so promotion FAILS.
The 10x value retained from D79 is diagnostic transparency:the failure is traceable to specific
aligned/residual evidence rather than a hidden model score. Its limitation is now measured—a scalar
bilateral-residual threshold is still insufficient. Preserve v1 source/raw/results immutably;any
next attempt must use a new public design,version and pre-retrieval freeze rather than retuning v1.
Evidence:`docs/evidence/human-knowledge-identity-contradiction-development-v1.md`;18 focused/788 full
tests PASS.

# D81 — Build one query-global envelope before evaluating any candidate

Status:ACCEPTED for HIE planning and HIE-T1,2026-09-21. The owner confirmed requirements,design and
the ordered task list before implementation. Build the public anchor index only from committed
casting and approved-alias text,then create one immutable envelope and checksum per query. Every
candidate must receive those same bytes;candidate-specific span choice is no longer decision input.

Conserve digit runs and alphanumeric model frames as categorical evidence. Permit only the general
same-anchor leading-year rule where a two-digit token equals the suffix of a four-digit`19xx`or
`20xx`token. Do not use release metadata,private evidence,case exceptions or another scalar
bilateral-residual threshold. Preserve HIC-v1 source and artifacts unchanged.

This has a 10x auditability advantage over an opaque cross-encoder because every envelope boundary,
token offset,model frame,numeric relation and shorthand decision is deterministic and inspectable.
The trade-off is that a corpus-wide lexical anchor may still choose the wrong identity boundary for
reordered or context-heavy queries. HIE-T2 must therefore evaluate predeclared structural policies
against historical public evidence before any new holdout is visible. HIE-T1 verification:11 new
focused tests and63 related tests PASS;zero artifacts,retrieval calls or runtime changes.

# D82 — Complete the phased v2 engine but let historical calibration stop the experiment

Status:ACCEPTED for HIE-T2,2026-09-21. Implement five predeclared categorical rank-1 policies,
preserve the0.75 secondary gate and source order,and rescore the immutable223/v4-22/HIC-v1-24
public rows without retrieval. Add deterministic protocol,pack,raw,selection and check interfaces,
but require at least one non-reference historical survivor before protocol bytes can be written.

Treat `query_only`and`candidate_only`numeric evidence as explicit states,not automatic compact-digit
failure. The guard fails on incompatible conserved digit runs;stricter policies may still reject
one-sided evidence through residual/form rules. This corrects the implementation to the confirmed
structural contract without adding a threshold,casting exception or private label.

The measured calibration currently has zero survivors. Numeric admission leaves7/12 v4 and7/12
HIC negatives nonempty while losing8 existing,1 v4 and1 HIC positive. Bilateral admission reduces
both negative sets to1/12 but preserves only146/168 existing,9/10 v4 and10/12 HIC positives.
Safe-form and decision-list lose still more recall. HIE-T3 must preserve this FAIL and create no
protocol or new holdout. The 10x auditability value remains:every loss and false admission has a
deterministic envelope,state and reason code. The decisive failure is generalization across valid
positive forms,not implementation integrity. Verification:23 focused/75 related tests PASS;zero
new retrieval calls,artifacts or runtime changes.

# D83 — Preserve the HIE-v2 historical FAIL before spending new retrieval

Status:ACCEPTED,2026-09-21. Run pre-freeze QA,then execute the historical calibration gate against
exactly223 existing,22 anchor-v4 and24 HIC-v1 public rows. Pre-freeze75 and final77 related tests
plus static checks pass,
and all policies produce zero envelope errors,but no non-reference policy satisfies every frozen
recall and absent-identity gate.

Do not freeze a protocol. Preserve deterministic calibration JSON,Markdown and manifest instead;
bind the exact HIE source and upstream evidence hashes. Repeated`--freeze-protocol`must return
`calibration_failed_unchanged`,and`--check`must recompute the same FAIL with winner null. Create no
negative declarations,holdout pack,raw rows or selection report,and execute zero new retrieval.

The closest structural policy,bilateral,reduces v4 and HIC absent-identity nonempty cases to1/12
each but preserves only146/168 existing,9/10 v4 and10/12 HIC positives. This is a measured product
failure,not an implementation failure. Integrity,auditability,privacy and reproducibility PASS;
historical positive preservation and safety FAIL. Block HIE-T4–T7 and every private/runtime step.
Any new attempt requires a new version and specification rather than modifying this frozen evidence.

# D84 — Publish the stopped HIE-v2 experiment as a null-result repository closure

Status:ACCEPTED,2026-09-22. HIE-T3 blocks the conditional holdout branch,but the failure evidence is
valuable and must remain reviewable. Add a requirements-to-evidence QA review,a public evidence
summary,an AI-eval rubric and a concise README section. Keep HIE-T7's successful-holdout checkbox
open;record repository delivery as a separate closure so a Git commit cannot be mistaken for policy
eligibility.

Preserve the frozen source and calibration hashes. Do not create protocol,pack,raw,selection,private
evaluation or runtime artifacts. Full repository tests pass813/813;targeted static checks pass.
Repo-wide Ruff/MyPy remain known debt(83 formatting candidates and51 type issues),so closure must
report them rather than mass-format unrelated history or mutate the frozen experiment after seeing
its result.

The 10x value of this delivery is auditability of a negative result:the repository shows exactly why
the method stopped before32 additional retrieval calls and which gate failed. Product eligibility
remains FAIL;implementation integrity,reproducibility,privacy and release safety PASS. A future
algorithm requires a new v3 namespace;static cleanup requires a separate behavior-neutral task.

# D85 — Build a candidate-independent local-frame claim graph before policy evaluation

Status:ACCEPTED for HICG planning and HICG-T1,2026-09-22. The owner confirmed requirements,design
and the ordered eight-task list before implementation. Replace HIE-v2's one linear envelope with one
immutable query graph built from the complete committed public identity corpus before any Top-5
candidate is inspected. Give identity,context,unresolved claims and each local numeric/model frame
separate roles,edges and deterministic checksum.

Use a frozen public context vocabulary with identity precedence;candidate-independent compact
segmentation;unique prefix abbreviation;alphabetic Damerau-Levenshtein edit1;and four bounded
numeric rules(year suffix,`o/0`,repeated-digit restoration and leading-year uncertainty`x`). Preserve
all source forms and reason codes. Do not read private evidence,expected labels,series,color,release
metadata or case-specific mappings.

This has roughly a10x auditability advantage over a learned cross-encoder:each normalization,
segment,role,frame owner,equivalence and checksum is directly inspectable. The trade-off is a larger
evidence schema and less semantic flexibility. The most likely failure is a corpus-wide hypothesis
that assigns an ambiguous word or digit to the wrong local slot;HICG-T2/T4 must expose that through
candidate evidence and exact historical gates rather than hiding it with a score.

T1 verification:the actual142-document corpus yields240 normalized forms and475 identity atoms;
20 focused and165 related identity/anchor/HIC/HIE tests PASS. Targeted Ruff,Mypy and compile PASS;
zero artifacts,retrieval calls or runtime/database/canonical changes. Candidate decisions and policy
eligibility remain unimplemented until HICG-T2.

# D86 — Run primary-casting hard-conflict preflight before every rank policy

Status:ACCEPTED for HICG-T2,2026-09-22. Compare the immutable query graph with both the candidate's
primary casting and approved aliases,but let aliases improve only positive alignment. A conflicting
numeric/alphanumeric frame in the primary casting remains a hard conflict even if a shorter alias
omits that frame. Apply this preflight at ranks1–5 before rank-specific coverage or admission logic.

Freeze one reference policy and four non-reference policies in declared order:conflict veto,
bilateral residual control,query conservation,and decision list. This categorical family was chosen
instead of tuning another scalar threshold because each stricter policy represents an inspectable
claim about what information may remain unexplained. The existing `>=0.75` secondary coverage check
therefore remains a downstream gate rather than an override for structural contradictions.

The main safety problem solved is the old branch order:secondary `R32`/`R33` queries could admit a
`BNR34` candidate from coverage alone,while alias selection could potentially conceal the numbered
primary form. T2 now abstains from those cases at both rank1 and rank4 with explicit frame and reason
evidence,while bounded year,OCR,repeated-digit,uncertainty,abbreviation,and compact-form positives
remain admissible under their declared structural relations. Candidate outputs preserve source order.

The 10x value is decision auditability:reviewers can inspect the immutable graph,selected form,
primary comparison,residuals,hard-conflict state,rank rule,and reason codes without reconstructing a
hidden score. The trade-off is conservative abstention when the local-frame owner or corpus grammar
cannot resolve a legitimate form. Historical calibration in HICG-T3/T4 must measure that recall cost;
T2 does not claim policy eligibility.

Verification:34 focused and179 related identity/anchor/HIC/HIE tests PASS. Targeted Ruff,Mypy and
compile PASS;only the existing Starlette/AnyIO deprecation warning remains. No protocol,pack,raw,
calibration,selection,retrieval,runtime,database,canonical,or color behavior was created or changed.

# D87 — Separate experiment machinery from the formal historical branch gate

Status:ACCEPTED for HICG-T3,2026-09-22. Implement every historical loader,gate calculator,phase
command,builder and validator before executing the formal223/22/24 calibration. T3 tests the
machinery with synthetic or temporary evidence and inspects only public input hashes and holdout
availability;HICG-T4 is the first step allowed to persist or act on the actual policy results.

Bind the five frozen HIC/HIE hashes before graph construction,then bind every corpus/evidence input
and the current V3 source hash into calibration and downstream manifests. Expose exactly five
mutually exclusive actions:`--freeze-protocol`,`--freeze-pack`,`--collect`,`--score`,and`--check`.
Each action validates every prior phase;existing bytes return `unchanged`,while stale hashes,
partial directories,phase skips,denominator drift,forbidden raw labels,or overwrite attempts fail.

The branch rule is asymmetric by design. A historical FAIL may create only deterministic calibration
JSON/manifest/Markdown with `winner:null`;a protocol requires a non-reference survivor. Pack creation
then proves16+16 balance,16 distinct positive documents/families,four positive and four negative
challenge groups,corpus-absent negatives,and zero retrieval. Collection alone may make exactly32
Top-5 calls;raw bytes exclude labels,decisions,gates and winners. Scoring must reuse those bytes.

This has a10x governance advantage over one command that both experiments and collects:the project
can stop before spending retrieval or exposing holdout outcomes,and each persisted byte states which
frozen inputs authorized it. The trade-off is a larger lifecycle implementation and stricter recovery
from partial artifacts. The most likely failure is contract drift between old public row schemas and
the V3 scorer;49 focused contract tests plus194 related regressions cover the current boundary,but
T4 remains responsible for the real denominator/gate run.

Verification:the installed CLI help exposes only the five phases;targeted Ruff,Mypy and compile PASS;
49 focused and194 related tests PASS. The real historical calibration was deliberately not executed,
and no V3 calibration,protocol,pack,raw,selection,retrieval,runtime,database,canonical,or color
artifact/change exists.

# D88 — Stop HICG-v3 at the historical gate with a null winner

Status:ACCEPTED,2026-09-22. After pre-freeze QA passed,execute the formal223/22/24 public historical
calibration exactly as specified. No non-reference policy passes all14 exact gates,so persist only
the deterministic calibration JSON,manifest and Markdown with `winner:null`. Do not create a
protocol,16+16 pack,label-blind raw rows,selection,private evaluation or runtime integration.

The result exposes a real safety/recall boundary rather than one universal winner. The two looser
policies preserve more positives but remain unsafe:`claim-conflict-veto` keeps166/168 existing,
9/10 v4 and12/12 HIC positives,yet admits11/12 v4 and10/12 HIC negative cases and misses both known
secondary BNR34 vetoes. The three structural policies reject both known conflicts and reach0/12 on
both negative sets,but preserve only134/129/131 existing positives,4/3/4 v4 positives and8/12 HIC
positives;they also keep only19/8/3 of24 prior required targets.

This negative result prevents32 new retrieval calls and blocks a misleading release claim. Its10x
value is evidence that the lifecycle gate can reject both an unsafe high-recall method and an overly
restrictive safe method before holdout collection. The trade-off is no v3 policy promotion. The
most important future research question is whether a new version can distinguish harmless residual
context/alias structure from true identity substitution without reintroducing the all-rank numeric
conflicts;V3 must not be retuned after observing this result.

Reproducibility:pre-freeze source SHA-256 is
`998f5af0983517d5ead54cf5fddaf46a57056245f92ac6d0c00c3279260ab173`;repeat freeze returned
`calibration_failed_unchanged`,and `--check` returned `valid`. Calibration hashes are JSON
`d2d94334d311c84e17c98b2f7d38876674ecf9def1c0dda6c889fbc822a7b1c2`,manifest
`9666ff2b5c63677fbc6f74daf9f4490e191c9a209151c798e44e75cccb2cac5f`,and Markdown
`16f5b425c6c3e4f7947f868112663a1e024c0270484ebea34fcfe7f583b460a5`. Denominators are exact,
retrieval/graph/alignment/decision errors are all zero,and API/Dual RAG/PostgreSQL/canonical/release/
color behavior remains unchanged. Two measured-artifact regressions lock the null branch and hashes;
the final T4 counts are51 focused and196 related tests PASS.

# D89 — Publish HICG-v3 as an implementation PASS and product-eligibility FAIL

Status:ACCEPTED,2026-09-22. Close the historical-FAIL branch with a requirements review,immutable
evidence summary,AI-eval rubric,README explanation and repository delivery. Keep four verdicts
separate:implementation integrity PASS;historical eligibility FAIL;holdout NOT RUN;runtime NOT
AUTHORIZED. A green test suite must not be presented as a qualified retrieval policy.

Preserve the V3 source and three calibration artifact hashes. HICG-T5–T7 remain conditional tasks
blocked by the null historical gate;do not manufacture protocol,pack,raw or selection artifacts to
make the task list look complete. The five policy results show the reason:loose policies preserve
recall but admit absent identities,while strict policies reach zero measured negatives at severe
positive loss. Selecting a closest policy would violate the exact predeclared gates.

This closure makes a failed experiment useful and reviewable:it proves the branch gate prevented32
unnecessary retrieval calls and blocked unsafe promotion. Full QA passes51 focused,196 related and
864 repository tests plus targeted Ruff,target-local strict MyPy,compile,installed CLI,integrity and
diff checks. Repository-wide MyPy's51 known existing/cross-module errors remain disclosed debt. No
API,Dual RAG,PostgreSQL,canonical,release or physical-feature behavior changes. A future algorithm
must use a new versioned spec/source/evidence namespace rather than retuning this frozen result.

# D90 — Propose corpus-wide minimal identity certificates for the v4 experiment

Status:CLOSED HISTORICAL FAIL; HICS-T1–T5/T9 complete and HICS-T6–T8 blocked,2026-09-24. Do not retune HICG-v3. Its
measured result shows that candidate residual symmetry is too strict for legitimate shorthand,while
manufacturer/shared-token compatibility is too weak for corpus-absent identities. Define the next
public-only attempt around corpus-wide minimal certificates:the smallest atom/frame combination that
uniquely identifies one committed knowledge ID.

Build the query support set against the full frozen certificate inventory before inspecting
retrieved candidates. A candidate can be admitted only when the query satisfies a complete
certificate for exactly one knowledge ID and the candidate maps to that ID without a primary-frame
conflict. This permits a unique shorthand to omit the rest of a long casting name,but prevents
`Honda Accord` from becoming Honda Civic merely because both share`Honda`.

The approximately10x auditability advantage over a learned reranker remains:each certificate has a
minimality proof,competing identities,source positions,equivalence uses and checksum. Feasibility
review found that142 documents represent139 casting/family authorities:three extra provisional
documents share the `83 Chevy Silverado` or`Toyota Supra` casting. Certificates therefore bind
authority keys rather than variant document IDs;primary castings create claims and aliases can only
bridge to them. This prevents forbidden series/color evidence from manufacturing variant identity.

The main risk is certificate instability or over-specificity in the small public corpus;historical
exact gates must run before any new retrieval. The owner bounded v4 as the last identity-admission
attempt before returning to the original Pointwise-versus-Listwise milestone. Requirements and
design and tasks are confirmed. The nine-task plan keeps T1–T4 in an isolated zero-retrieval build phase,
makes T5 the mandatory historical branch gate,permits T6–T8 only after PASS,and uses T9 to close
either branch before the reranker handoff. HICS-T1 now validates 142 documents as 139 authority
keys with immutable upstream/corpus bindings. HICS-T2 derives460 primary-only claims,401 minimal
certificates and101 alias bridges. Seven shorter primary names remain unresolved because their full
claim sequence is contained by another authority;series/color evidence is not allowed to separate
them. HICS-T3 now computes query support before candidates,with categorical exact/structural/bounded
relations,residual and ambiguity fail-closed behavior,and one checksum reused by all candidate ranks.
HICS-T1–T3 evidence remains in memory,and no holdout,private evidence or runtime change is approved
by this decision alone. HICS-T4 implemented immutable public loaders,exact 223/22/24 offline scoring,
the conditional null/PASS artifact lifecycle and the five-phase installed CLI. HICS-T5 then ran the
formal gate once with zero retrieval. Exact,structural and bounded profiles preserved42,82 and137 of
168 required existing positive hits;all three reached zero absent-identity output,2/2 secondary
numeric vetoes and zero computation errors,but none passed every positive gate. The branch therefore
freezes `winner:null` and only three calibration files. Protocol,inventory,holdout,raw,selection,
private evaluation and runtime changes remain unauthorized;HICS-T6–T8 are blocked and HICS-T9 must
close this final identity-admission attempt before the Pointwise/Listwise handoff.

# D91 — Use one frozen MiniLM Cross-Encoder and one small candidate-set attention head

Status:CLOSED NULL RESULT; NRC-T1–T10 complete,2026-09-25. Compare the unchanged canonical
RRF order with exactly one neural pointwise model and one neural listwise model on byte-identical
candidate pools. Pointwise uses revision-pinned Apache-2.0
`cross-encoder/ms-marco-MiniLM-L6-v2` locally in CPU float32 with frozen weights. Listwise consumes
the same pointwise logit plus a fixed21-feature RRF/source/structured vector through a32-dimensional,
one-layer,self-attention head without positional embeddings and trains with a masked listwise
softmax objective on matched Train lists only.

The decision deliberately rejects two attractive but misleading alternatives. It does not call the
existing lexical `heuristic-v1` a neural baseline,and it does not fine-tune22.7M transformer
parameters on only36 matched Train queries. It also avoids a model-zoo search that could select a
checkpoint around12 matched Test cases. The bounded hypothesis is whether a credible pretrained
pair scorer and explicit candidate-relative context improve near-duplicate ranking;no improvement
must remain publishable as `winner:null`.

The10x value is architectural clarity per unit of data:one shared neural text score allows the
experiment to isolate what list context adds,while the small head keeps every non-text feature and
relative interaction inspectable. Value is a resume-visible Pointwise/Listwise comparison;
correctness comes from family splits,one-time Test and paired metrics;maintainability comes from two
isolated experiment modules and optional imports;security comes from safetensors,immutable revision,
no remote code and offline inference;performance is bounded by batched Top-25 CPU scoring;
reproducibility comes from fixed schema,seed,hashes and exclusive phase artifacts.

The main trade-offs are domain mismatch and small-sample variance. A frozen MS MARCO reranker may
not understand year/color/collector distinctions,and a listwise head trained on36 lists may not
generalize. The most likely engineering failure is accidental candidate-position or padding leakage;
batch-order,padding-mask and permutation-equivariance tests therefore block formal Test collection.
Even a passing result is shadow-only:runtime,calibration,API,Dual RAG,PostgreSQL and canonical data
stay unchanged until a separate integration spec.

NRC-T2 now makes the pointwise model boundary executable without acquiring the model. The optional
extra remains outside the default install; one immutable config binds model ID,revision,Apache-2.0,
CPU float32 and the exact six-file safetensors/tokenizer allowlist. Acquisition is the only
network-capable function and requires explicit license confirmation. It converts any download-cache
symlinks into validated regular local files,records every SHA-256,and refuses unexpected,pickle/code,
missing or tampered bytes. The scorer validates that manifest before lazy imports and passes
`local_files_only=True`,`trust_remote_code=False` and `use_safetensors=True` through the verified
Sentence Transformers3.4.1 interface. No package/model was installed or downloaded;formal state
remained absent before the NRC-T3 implementation described below.

NRC-T3 now implements the second architecture behind the same lazy optional boundary. Only the
pointwise logit and RRF score receive Train-fitted population normalization;the other19 binary and
reciprocal-rank features remain byte-for-value unchanged. The candidate encoder is exactly
Linear(21,32)／GELU／LayerNorm followed by one four-head,64-feedforward,zero-dropout Transformer
encoder and a scalar head. No positional parameter exists,and padding is passed as
`src_key_padding_mask` then forced to negative infinity before listwise cross-entropy. Training fixes
CPU float32,seed20260924,AdamW1e-3／1e-4,batch8,100 epochs and10-epoch patience;strict Dev MRR
improvement means ties retain the earlier checkpoint.

The checkpoint contains model tensors only in safetensors;optimizer state is excluded. Its JSON
manifest binds the exact21-feature order and hash,architecture,seed,selected epoch,Train normalizer,
tensor names/shapes and checkpoint hash. The default environment intentionally still lacks Torch:
two real-tensor permutation/padding/loss/repeatability tests are collected and skipped until the
owner-approved NRC-T7 optional install,while dependency-free wiring and lifecycle tests pass now.
This preserves the agreed supply-chain sequence rather than silently installing a large package.
NRC-T4 now implements that protocol/pool boundary without creating formal state. The protocol binds
the exact benchmark, catalog, model config, dependency versions, implementation sources and future
pointwise manifest hash. Pool construction reads only the ordered58 Train and21 Dev query fields,
calls the unchanged sparse/dense/structured RRF service exactly once per case,then freezes Top-25
identity/text/source-rank/source-score/structured-evidence/RRF/timing data. Recursive validation bans
labels, metrics and neural outputs; exact query projection, family split validation, canonical JSON,
SHA-256 manifests and exclusive whole-directory publication make partial,drifted or tampered state
fail closed. Repeating a valid freeze returns `unchanged` without retrieval or overwrite.

All lifecycle proof used temporary fixtures. Eight focused tests and the954-pass/2-skip full suite
pass;the two skips remain the intentionally deferred real-Torch tests. Formal data,reports and model
cache remain absent,with no network,dependency install,training,Test collection,API,Dual RAG,
PostgreSQL or runtime change. NRC-T5 may add only synthetic Train/Dev fitting and immutable model
selection lifecycle code;the external model and formal freeze remain gated until NRC-T7.

NRC-T5 now makes that selection boundary executable without running the formal experiment. It
scores every frozen Train/Dev candidate as an independent query/text pair,records deterministic
pointwise ranks,and verifies the pretrained manifest hash before and after both scoring and listwise
fitting. Labels join only at the orchestration layer:ambiguous/no-match rows are excluded,matched
targets absent from the pool become retrieval misses,and only matched Train targets already present
become listwise examples. Dev examples never fit weights or normalization;they only determine the
earliest best epoch under the fixed patience rule.

The three-file `models/` phase is exclusive-create and immutable. Pointwise metadata binds the local
model,protocol,pool,input schema,dependencies and all label-free Train/Dev logits/ranks. Listwise
metadata binds the21-feature order,fixed architecture/AdamW hyperparameters,seed,Train-only
normalizer,training-label checksum,eligibility counts,full Train-loss/Dev-MRR history,selected epoch
and safetensors checkpoint bytes. A valid repeat returns `unchanged` before scoring or training;
partial state or config,pool,dependency,pointwise-model or checkpoint drift fails without overwrite.

All proof remains synthetic and temporary. Four new integration tests bring lifecycle coverage to12;
related QA is45 passed/2 skipped and the full suite is958 passed/2 skipped across960 tests. No model
download,optional install,formal fit,Test collection,API,Dual RAG,PostgreSQL or runtime change
occurred. NRC-T6 may implement only synthetic one-time Test/report/CLI machinery;external acquisition
and every formal phase remain gated until NRC-T7.

NRC-T6 now makes the complete one-time Test boundary executable without consuming the formal Test.
Before collection it checks pointwise batch-order and listwise permutation invariance,then warms both
scorers on Train/Dev-only rows. Each of the21 Test queries is retrieved once into one shared ordered
candidate list;RRF,pointwise and listwise records clone those identities and may only change rank and
score. Errors are frozen in place and never retried,so a later success cannot selectively replace a
bad observation. Recursive validation keeps labels,metrics and recommendation fields out of raw data.

The separate scoring phase is the only path that loads Test labels. It hashes model/raw state before
and after scoring,retains raw ranking scores as explicitly non-calibrated evidence,and computes exact
overall/category metrics plus paired rank transitions. A neural arm can win only if it gains at least
0.05 Top-1,does not reduce hard-negative accuracy,MRR or Recall@25,keeps resolver p95 at or below
1500 ms,and has zero errors. Eligible ties resolve by hard-negative accuracy,Top-1,MRR,lower p95 and
then the simpler pointwise arm;otherwise the honest result is `winner:null`.

Canonical JSON,Markdown and two deterministic SVG charts expose denominators,disclaimers,shared
candidates,all arm scores/timings,model versions and evidence scope. Manifests make partial or
tampered raw/report state fail closed and prevent overwrite. Eleven new synthetic tests bring the
lifecycle suite to23;related QA is56 passed/2 skipped and full QA is969 passed/2 skipped across971
tests. No
formal artifact/model cache,network,download,real Test collection or runtime change occurred. NRC-T7
is now the next task and still requires explicit owner approval for optional dependencies and the
pinned model acquisition.

NRC-T7 consumed that one-time approval and established the first formal external state without
touching Test. The project-local virtual environment now contains Sentence Transformers3.4.1,
Torch2.7.1 and safetensors0.5.3;the actual reference Mac/Python3.12.13 resolution is recorded as33
direct/transitive pins rather than pretending the original three direct constraints were a complete
lock. All74 installed packages pass compatibility checking,and the formerly skipped real tensor
tests now pass.

The only acquired pretrained artifact is Apache-2.0
`cross-encoder/ms-marco-MiniLM-L6-v2` revision
`233902d25c440f23af6f7d6e94d2946bac0bee0a`. Exactly six config/tokenizer/safetensors files were
copied as regular local files;the88 MB snapshot manifest hash is
`32f889bb415ef5a56760a299da0635e8e1704d46fe0b11ded06c563de896feb8` and offline-only loading plus
real pair scoring succeeds. A second acquisition returns `unchanged`,so network state cannot rewrite
the frozen model.

The formal protocol remains `frozen_pre_test`:it binds the100-case family-disjoint benchmark,
120-product `fixture-v1` catalog,source/code/config hashes,canonical retriever and resolved core
dependencies. The label-free pool contains58 Train and21 Dev rows with1,973 candidates,zero empty
candidate rows and zero candidates without source evidence. A second freeze returns `unchanged` and
full check returns `valid`;models,Test raw and reports are absent. Related QA is58/58 and full QA is
971/971. NRC-T8 may now fit only Train/Dev artifacts under these frozen inputs;formal Test remains
gated behind the later one-time collection task.

NRC-T8 froze the formal model-selection state under offline-only execution. The unchanged MiniLM
base scored all79 Train/Dev rows and1,973 frozen candidates;its manifest confirms frozen weights,
the approved revision/model hash,finite deterministic logits and no Test access. All36 matched Train
and12 matched Dev targets were already present in their pools,so retrieval misses are zero;the22
Train and9 Dev ambiguous/no-match cases remain excluded rather than being converted into positives.

Only Train fit the normalizer and candidate-set head. Dev MRR@10 equaled1.0 at every observed epoch
from1 through11. The fixed rule requires strict improvement and stops after10 stale epochs,therefore
epoch1 is selected. Choosing epoch11 because its Train loss is lower would be post-hoc overfitting:
Dev showed no ranking benefit,while the earlier checkpoint is the simplest model supported by held-out
selection evidence. The selected safetensors checkpoint hash is
`9386c0593ec07ad2b9eb0f6daa613b66f7b117e0e6c5a33be2e8705dbe18aead`.

Real checkpoint preflights prove pointwise batch-order invariance,listwise candidate-permutation
equivariance and padding isolation. Repeat fit returns `unchanged`,full check returns `valid`,related
QA is58/58 and full QA is971/971. No Test label/score/raw/report exists. NRC-T9 is therefore the next
and only label-blind Test collection;after that collection v1 source,config,model and hyperparameters
cannot change.

NRC-T9 executed the one permitted formal Test collection only after every frozen source/config/model
hash revalidated and raw/report state was absent. Exactly21 unique Test queries produced exactly21
canonical retrieval calls,zero errors and25 candidates per row. The resulting525 candidate
observations are shared by all three arms:RRF preserves source order,and both neural arms contain the
same UUID set while changing only scores/ranks. No candidate was added,dropped or substituted.

The raw manifest is explicitly label-blind and binds protocol,pool,pointwise manifest,listwise
manifest/checkpoint and Test-query source. Recursive inspection found no expected,target,label,
accuracy,metric,winner or eligibility key. Raw SHA-256 is
`948582264e67ad6d686a4409a41100149118d12b6e4548bbdc1265d778756884`;a second collection returns
`unchanged` and full check returns `valid`. Related QA remains58/58 and full QA971/971. From this
point v1 source,config,model and hyperparameters are immutable;NRC-T10 may only join labels once,
publish the predeclared metrics/gates and add measured-artifact regression plus closure documents.

NRC-T10 joined labels once and closed the hypothesis without changing the frozen experiment. RRF,
neural pointwise and neural listwise each achieve Top-112/12,MRR@10 12/12,Recall@10/25 12/12 and
matched hard-negative accuracy4/4. Both neural paired-transition sets are twelve rank1→1 unchanged
cases. Listwise candidate context therefore provides no measured ranking improvement on this Test.

The neural arms are operationally valid:pointwise/listwise resolver p95 is89.164/89.583 ms,both far
below the1500 ms budget,and collection errors are zero. They still fail the most important gate:
Top-1 absolute gain over RRF is0.00 rather than at least0.05. The decision is `winner:null`;choosing
the faster pointwise arm or more sophisticated listwise arm despite zero value would violate the
predeclared selector and add roughly88 ms p95 to an already-correct fixture ranking.

The null result is bounded to a12-matched-case synthetic/curated fixture Test with a ceiling baseline.
It does not prove that neural reranking is generally ineffective. It does prove that the project can
separate Pointwise and genuine Listwise architectures,use one-time label-blind evaluation,preserve
local-model provenance,and publish a negative result without inflated resume claims. RRF remains the
runtime default;any future attempt needs a non-ceiling benchmark and a separately frozen v2 rather
than modifying v1.

## 2026-10-05 — RHB-T6 readiness blocks labeling before owner effort

**Decision:** add a read-only, hash-bound RHB-T6 entry validator and stop before presenting an Owner
Gate. Do not patch the frozen T1/T3 decisions in place and do not create partial labels.

The readiness check found that all 60 queries come from a source permitted to produce only
`ambiguous/no_match`, making the required matched composition `0/20`. It also found that CAR's Wiki
evidence source, although later accepted by the separate CAR workflow, remains prohibited for exact
authority in the frozen RHB T1/T3 contract. A versioned governance repair is therefore required
before owner labeling.

The 10x alternative would be to label all 60 rows immediately and resolve contract errors later.
That appears faster but risks wasting the owner's highest-cost review work and creates labels that
cannot pass the evaluator. The selected method spends a small deterministic validation step first,
keeps historical decisions immutable, and exposes exact blockers before asking for new authority.

The most likely failure is an over-broad repair that treats Human labels or the whole Wiki dataset
as canonical truth. Any proposal must instead admit only the narrowly reviewed CAR bundle and allow
a matched query label only when it binds an independent admitted authority record. Manufacturer or
global truth remains out of scope.

The chosen proposal now implements that design boundary as data rather than prose. One admission is
bound to the current 60-row query-pack hash; the other is bound to the current 20-record CAR authority
hash. This two-hash overlay is preferred over a source-wide T1/T3 mutation because it preserves the
historical decision and makes authority expansion mechanically impossible without a new version.

Across six dimensions the overlay proposal is: strong on correctness (exact parent binding),
security/privacy (no row-level query/label), maintainability (one strict schema), observability
(explicit 0/20 and 16-shortfall parents), reversibility (proposal only, no mutation), and portfolio
clarity (demonstrates governed evidence evolution instead of silent permission changes). Its cost is
one extra Owner Gate before labeling; that is acceptable because owner review is the scarce and
irreversible resource being protected.

## 2026-10-05 — Materialize a two-hash governance overlay without rewriting T1/T3

**Decision:** accept the owner's RHB-T6 Governance Repair v1 authorization only as permission to
materialize a versioned overlay. Bind matched-label permission to query pack SHA `97f7…858a`; bind
canonical authority to the 20 sorted IDs in CAR bundle SHA `72c1…3117`. Keep label authoring, split
assignment and resolver evaluation behind separate future Gates.

The alternative of editing frozen T1/T3 was rejected because it would make the earlier audit look as
though the later evidence had always existed. Promoting all Wiki rows was also rejected: CAR review
established 20 exact records, not source-wide manufacturer-grade reliability. The overlay preserves
both facts by leaving old files unchanged and carrying the exception as a new, hash-bound artifact.

The 10x alternative would be a generic policy engine for arbitrary source/record overrides. That is
unnecessary for this portfolio-sized pilot and would enlarge the trust surface before a second use
case exists. A strict Pydantic model with fixed parent hashes, fixed count, sorted allowlist and
negative authorization flags is smaller, auditable and fail-closed.

The most likely failure is scope creep during downstream validation—for example, accepting another
query pack because it shares a source ID, or any record from the same Wiki revision. Core validation
therefore checks the exact query-pack content hash, full authority-bundle hash and allowlisted IDs.
Post-overlay readiness separately reports that frozen source-wide compatibility remains false. This
makes the distinction between a narrow exception and global promotion visible in both code and QA.

## 2026-10-05 — Stage label review conservatively; do not confuse permission with evidence overlap

**Decision:** use the RHB-T6 authorization to create only local evidence packets and staged proposals.
Do not materialize labels until the owner adjudicates each row or batch. Candidate discovery may use
exact catalog casting/alias and alphanumeric toy-identifier surfaces, but may not call the resolver,
rank candidates, consult old labels/failure categories, or allocate a benchmark split.

The 10x alternative would auto-label all catalog-absent surfaces as `no_match` and tune fuzzy matching
until 20 authority records appear as `matched`. That would produce the desired denominator quickly,
but it would violate the owner's quota-forcing prohibition and turn alias coverage into false ground
truth. The selected method leaves uncertain rows held and publishes the shortfall.

The first staging run finds zero uniquely matchable authority rows. Governance allows up to 20
matched labels, but the selected 60 real noisy queries barely overlap the seven admitted authority
families. One private row hits three releases and cannot identify which UUID is correct. This
distinction is now explicit: authority admission answers “may this identity be used?”, while evidence
overlap answers “does this query justify that identity?”. Both must pass.

The most likely failure is pressure to treat the staging counts as final labels or to repair the
denominator inside the same Gate. Prevent that by keeping every proposal non-score-eligible and
requiring an owner event before materialization. If owner review confirms insufficient matched
coverage, the correct next design is a separately versioned source/query-pack expansion, not a
silent RHB-T5 rewrite or synthetic padding.

## 2026-10-05 — Preserve owner review as private append-only events

**Decision:** record each RHB-T6 owner-review batch as an immutable private event and publish only a
hash-bound aggregate progress artifact. Do not mutate AI-generated staged proposals and do not
materialize a partial label set while review is incomplete.

The first batch covers ten staged cases: one approved catalog-relative `no_match` decision and nine
holds. All provisional challenge tags remain unverified, matched approvals remain zero and fifty
cases remain. The public record deliberately omits row identifiers, queries, per-row decisions,
review reasons, owner text and canonical UUIDs.

The alternative was to update proposal rows in place. That is smaller in file count but destroys the
distinction between model suggestion and human adjudication, weakens replay evidence and makes a
partially reviewed workspace look like a completed label set. Append-only events keep those trust
layers separate and allow every new batch to prove non-overlap with prior decisions.

The most likely failure is accidental downstream use of partial owner decisions. The progress
builder therefore verifies negative authorization flags and the absence of label/split artifacts;
the approved decision remains non-score-eligible until a separately authorized materialization
stage. This preserves the owner's explicit prohibition on RHB-T7, split, scoring and resolver
evaluation.

## 2026-10-05 — Treat `held` as an evidence state, not a negative label

**Decision:** keep all ten Batch 2 cases held because frozen evidence is insufficient. Catalog
absence alone does not establish that a marketplace item has no valid product identity, so these
cases must not be converted into `no_match` merely to increase benchmark coverage.

The progress artifact may advance only by appending a private owner event to a previously valid
history. Before replacing the aggregate snapshot, the builder recomputes its prior-batch prefix and
requires exact equality. This is preferred over blind overwrite because it preserves the separation
between immutable adjudication events and a replaceable public summary.

The consequence is deliberately conservative: twenty cases have been reviewed, but only one is an
approved label decision and none is matched. Nineteen held cases remain outside labels and scoring.
Future evidence can reopen them without rewriting the historical reason they were withheld today.

## D44 — Integrate Pointwise as a fail-closed provider before calibrating decisions

- **Choice:** add the frozen neural Pointwise ranker behind an explicit local-only provider, while
  keeping RRF as the default and requiring separately bound neural calibration and policy artifacts
  before API readiness can pass.
- **Reason:** the untouched 53-case test establishes ranking improvement, but CrossEncoder logits
  are not match probabilities. Reusing RRF or heuristic thresholds would combine independently
  validated components into an unvalidated decision system.
- **Alternatives:** immediately make Pointwise the default; reuse the heuristic calibrator; keep the
  model confined to experimental scripts until calibration is complete.
- **10x alternative considered:** deploy ranking and policy together in one large change and report
  only end-to-end accuracy. It is faster on paper but removes the ability to distinguish ranking
  gains from calibration errors and makes rollback less precise.
- **Most likely failure:** a user enables the neural provider with missing model bytes or stale
  decision artifacts. The provider therefore validates local hashes, artifact version binding and
  readiness before serving any request.
- **Impact:** runtime wiring is now testable and observable without changing defaults. The remaining
  work is narrow: select calibration and policy on the frozen development partition only. The final
  test remains immutable and cannot be used for threshold selection.

## D45 — Calibrate match acceptance on a nested development split without inventing no-match truth

- **Choice:** split the frozen 100-case development partition deterministically into 70 calibration-fit
  and 30 threshold-selection rows. Fit an exact-release correctness calibrator on the first group and
  select the highest-coverage threshold meeting at least 90% empirical precision and five accepted
  rows on the second. Mark all lower-confidence candidate-bearing cases ambiguous and publish the
  resulting policy with `runtime_eligible=false`.
- **Reason:** calibration fitting and threshold selection need separate evidence even within
  development. The available benchmark contains only catalog-present positives, so it can support
  matched-versus-ambiguous acceptance but cannot estimate a defensible no-match boundary.
- **Alternatives:** fit and choose a threshold on all 100 development rows; reuse heuristic/RRF
  calibration; treat low-confidence positive rows as synthetic no-match examples; inspect the frozen
  final test to improve the threshold. Each alternative either leaks selection evidence or answers a
  different question from real catalog absence.
- **10x alternative considered:** collect and independently adjudicate a large set of genuine
  catalog-absent queries before doing any calibration. That would support a complete production
  policy, but it is a separate data-governance project and would block learning whether Pointwise
  confidence has useful acceptance precision on the evidence already frozen.
- **Most likely failure:** reporting 90.91% accepted-row precision as overall resolver accuracy, or
  activating the policy despite zero no-match validation. The artifact therefore records 36.67%
  coverage, zero no-match labels, `test_cases_scored=0` and `runtime_eligible=false`; the service
  rejects it even under explicit neural-provider configuration.
- **Impact:** Pointwise now has reproducible development-only confidence mapping and a conservative
  abstention threshold. Runtime default remains RRF. A later runtime-eligible policy requires new,
  independently governed no-match development evidence and must not retune on the 53-case final test.

## D46 — Audit existing real queries before collecting or synthesizing no-match data

- **Choice:** use the existing human-reviewed noisy-name corpus only for its currently permitted
  future-catalog-alignment purpose. Count exact normalized brand/casting absences against the frozen
  1,763-record catalog, freeze the 52-row candidate-set digest and prospective 32/20 development
  split, but retain the original calibration and threshold-selection blockers.
- **Reason:** 52 confirmed real queries already reference families absent from the catalog snapshot.
  This is enough to support a later development experiment without more crawling, while the existing
  `excluded_from` contract means readiness cannot silently become authorization.
- **Alternatives:** synthesize unknown product names; reuse fixture no-match rows; reinterpret all 99
  old fixture-unmapped alignments as negatives; immediately score the 52 rows. These choices would
  either weaken realism, confuse different catalog snapshots or bypass an explicit data-use boundary.
- **10x alternative considered:** launch a new independently sampled and adjudicated negative-data
  collection with manufacturer-grade absence proof. It would provide stronger external validity,
  but it is unnecessary before measuring whether the already reviewed 52-row candidate set closes
  the development-only policy gap.
- **Most likely failure:** exact spelling absence may be reported as global product absence, or rows
  may be selected after viewing neural output. The artifact therefore says catalog-relative only,
  freezes membership/split hashes before scoring, and records zero resolver/model/final-test work.
- **Impact:** additional web collection is not currently required. One narrow owner authorization is
  now the sole prerequisite for a versioned usage overlay; calibration, policy replacement, runtime
  activation and final-test retuning remain unauthorized.

## D47 — Preserve the original source contract and express PNMR-G1 as a bound overlay

- **Choice:** record the exact owner response and materialize a versioned overlay bound to the human
  dataset, 52-row candidate set, frozen catalog and 32/20 split hashes. Grant only Pointwise
  development fit/selection permission; leave the original source exclusions untouched.
- **Reason:** editing `human_labeled_names.json` would falsely imply all rows had always been eligible
  for calibration. A narrow overlay preserves chronology and prevents the authorization from being
  reused with a different candidate set, catalog or split.
- **Alternatives:** remove the two source exclusions; rely on the chat message without an artifact;
  create a source-wide calibration permission. Each loses either auditability or scope control.
- **10x alternative considered:** implement a generic policy engine for arbitrary data-use grants.
  One bounded use case does not justify that framework or its larger authorization surface.
- **Most likely failure:** a later stage treats development permission as runtime or final-test
  permission. Both authorization and overlay carry explicit false flags, and downstream validation
  must require them before scoring.
- **Impact:** the 52 rows may now be used only in the frozen 32/20 development partitions. Runtime,
  final test, public row data and global no-match claims remain prohibited.

## D48 — Use two independent development gates and keep the resulting policy non-runtime

- **Choice:** fit one correctness calibrator on 70 catalog-present plus 32 governed no-match rows,
  then select match and no-match thresholds on the disjoint 30+20 partition. Require 90% precision
  for both decisive states and cap catalog-present false no-match at 10%. Keep the resulting policy
  `runtime_eligible=false` even when both development gates pass.
- **Reason:** a single match threshold cannot distinguish low-confidence ambiguity from true catalog
  absence. Separate gates make both error directions visible, while PNMR-G1 expressly withholds
  runtime permission.
- **Alternatives:** retain no-match threshold zero; classify every value below match threshold as
  no-match; tune on the existing final ranking set; activate v2 immediately after development PASS.
  These alternatives either eliminate ambiguity, lack negative truth or cross an authorization and
  evaluation boundary.
- **10x alternative considered:** train a dedicated out-of-distribution detector with a much larger
  multi-source negative corpus. That may improve no-match recall, but the present five-feature
  logistic layer is smaller, reproducible and sufficient to test whether governed negatives add
  useful abstention behavior before investing in another model.
- **Most likely failure:** presenting 100% match precision and 90% no-match precision as untouched
  production accuracy. They are threshold-selection metrics on 50 development rows, with only 14%
  matched coverage and 45% no-match recall. The artifacts and QA report state this limitation and
  block runtime use.
- **Impact:** the resolver now has a reproducible three-state development policy with 7 matched,
  10 no-match and 33 ambiguous decisions on selection. Any runtime gate requires a new untouched
  negative holdout and must evaluate the frozen v2 artifacts without retuning.

## D49 — Report a real holdout shortfall instead of relabeling derivative data

- **Choice:** audit the remaining local real-query files by case-ID overlap and human-answer
  completeness, then publish an aggregate `0/20` holdout-readiness result. Keep the one approved RHB
  no-match ineligible while its split, scoring and resolver-evaluation permissions remain false.
- **Reason:** all 52 useful catalog-relative no-match queries already participated in v2 fitting or
  threshold selection. The other 230 comparison rows and 1,640 evidence rows are derivatives of the
  same cases, while the four untracked rows in the 105-row queue have no human expected identity.
  Renaming any of these as an untouched test would create leakage rather than evidence.
- **Alternatives:** reuse the 52 development rows as test; treat the four ambiguous exclusions as
  negatives; create counterfactual or synthetic unknowns; count the one RHB decision despite its
  explicit permission boundary. All four options make the test larger by weakening its meaning.
- **10x alternative considered:** immediately collect hundreds of independently adjudicated organic
  no-match queries. That would improve statistical power, but the smallest honest next gate is 20;
  collecting more should be a separately authorized data task with cost and privacy controls.
- **Most likely failure:** a future maintainer sees multiple large CSVs and assumes they are new
  labels. The artifact freezes each source hash, unique-ID overlap, answer completeness and
  classification without copying row data, then fails closed if those aggregates change.
- **Impact:** Pointwise v2 remains development-only and runtime activation is blocked. The next
  eligible action is to collect and independently adjudicate at least 20 new organic queries,
  freeze them before resolver access and evaluate without changing the model, features or thresholds.

## D50 — Freeze the owner-reviewed holdout before any resolver access

- **Choice:** materialize Batch 1 as one minimal 20-row versioned dataset, bind it to the frozen
  1,763-record catalog and its pre-review lineage hashes, then delete the entire untracked collection
  workspace. Keep resolver scoring, model retuning, threshold retuning and runtime activation false.
- **Reason:** test membership and expected truth must exist before outputs are visible. Separating the
  data-freeze gate from the evaluation gate prevents a disappointing score from changing which rows
  count, how they are labeled or which threshold is selected.
- **Alternatives:** retain all raw Serper responses and images; publish source URLs and timestamps;
  run the resolver in the same approval step; append the rows to the positive evaluation dataset.
  These choices respectively increase privacy/repository noise, cross the owner's authorization, or
  erase the distinction between catalog-present and catalog-relative no-match truth.
- **10x alternative considered:** commission a large multi-source manufacturer-adjudicated negative
  benchmark. It would give stronger external validity, but it is unnecessary for the next bounded
  question: whether the already frozen development-only Pointwise v2 policy generalizes to 20 new
  catalog-relative no-match queries.
- **Most likely failure:** readers interpret a missing exact family in the 2023–2026 community
  snapshot as proof that the product does not exist. The dataset therefore names its scope as
  third-party-catalog-relative and tests the bound catalog hash before asserting absence.
- **Impact:** the data-readiness shortfall moves from 0/20 to 20/20 without producing an evaluation
  result. A separate owner gate is still required for one output-blind test, and that gate must not
  permit retuning or runtime activation.

## D51 — Evaluate rejection once and keep abstention visible

- **Choice:** execute PNMH-G2 once with the frozen Pointwise v2 calibration/policy/model and reduce
  20 in-memory outcomes to aggregate counts, rates, reason counts and confidence min/mean/max. Set
  the pre-score gate at at least five no-match decisions and at most two incorrect matches; keep
  ambiguous outcomes separate and keep runtime authorization false.
- **Reason:** the holdout contains only catalog-relative negatives, so the useful questions are how
  often the policy rejects, abstains or falsely matches. Row-level storage would make these final
  test cases tempting tuning material and would violate the owner's publication boundary.
- **Alternatives:** save per-query predictions for error analysis; turn ambiguous into no-match;
  change thresholds after seeing the result; report only a single accuracy number. Each option would
  either leak the holdout into development, overstate rejection quality or hide an important safety
  behavior.
- **10x alternative considered:** run a large balanced, manufacturer-adjudicated production-traffic
  benchmark with confidence intervals. That remains the stronger runtime gate, but it is a separate
  data and authority project; it cannot be substituted for the approved 20-row negative test.
- **Most likely failure:** present 0% false matches as complete resolver accuracy. This dataset has no
  catalog-present examples, so it cannot measure exact-match quality or false-no-match behavior on
  positives. QA and AI-eval evidence state that limitation explicitly.
- **Impact:** the frozen policy passes its bounded negative gate with 11 no-match, 9 ambiguous and
  zero matched outcomes. This supports conservative rejection behavior only; it neither retunes nor
  activates the resolver and cannot authorize runtime on its own.

## D52 — Accept the balanced evidence gate but hold runtime for low coverage

- **Choice:** evaluate the frozen v2 policy once on the fixed 53-case catalog-present test, reuse the
  existing 20-negative aggregate without rescoring, and publish casting, exact-release and combined
  metrics separately. Mark the preregistered gate PASS but keep runtime held.
- **Reason:** five accepted positives are all exact-release correct, false no-match is below 10% and
  the negative side has zero false matches. However, 54/73 combined cases abstain and positive exact
  recall is only 9.43%; high accepted precision alone is not sufficient product utility.
- **Alternatives:** lower the 0.9425 match threshold after seeing the holdout; count casting-correct
  rows as exact-release success; merge ambiguous into a success class; activate only because all
  formal minimums passed. Each option either leaks the test into tuning or hides the resolver's
  final-identity and coverage limitations.
- **10x alternative considered:** collect a new, larger, class-balanced production-like benchmark
  and train a stronger calibrated model on a separate development corpus. That is the correct future
  route to better coverage, but it requires new development data and a fresh final test rather than
  recycling these 73 cases.
- **Most likely failure:** market 100% matched precision without mentioning that only 5/53 positives
  were accepted. QA therefore pairs precision with recall, abstention and end-to-end exact accuracy,
  and describes the system as a high-precision abstaining prototype.
- **Impact:** the portfolio now has honest aggregate generalization evidence for both catalog-present
  and catalog-relative no-match inputs. It does not have runtime authority; any improvement cycle
  must avoid both frozen holdouts and later earn a new evaluation gate.

## D53 — Lead the portfolio with current evidence, not the saturated fixture

- **Choice:** retain confidence-aware entity resolution as the headline and Dual RAG as the internal
  authority architecture, but promote the 1,763-release/153-query ranking experiment and 73-case
  calibrated policy evaluation to the primary README evidence. Keep the old fixture null result as
  research history and rewrite the Portfolio Guide around three current claims.
- **Reason:** the old README accurately described an earlier milestone but now understated the
  project by leading with a 120-product saturated fixture. The later evidence demonstrates both a
  real Pointwise ranking gain and the discipline to withhold runtime when calibration coverage is
  poor.
- **Alternatives:** delete the fixture result; present only the 100% accepted precision; market
  Pointwise as deployed; leave the chronological homepage unchanged. These options respectively
  erase learning history, hide 73.97% abstention, misstate runtime or make the strongest evidence
  difficult for a reviewer to find.
- **10x alternative considered:** build a hosted interactive portfolio dashboard with live model
  inference and charts. It would be more visual, but it would introduce deployment claims and
  operational scope before the policy is runtime-ready. A concise GitHub landing page is the safer
  current artifact.
- **Most likely failure:** recruiters remember “100% precision” but miss that only five positives
  were accepted. README and the interview pitch therefore pair precision with `5/53` recall,
  `54/73` abstention and an explicit runtime HOLD every time the policy result is summarized.
- **Impact:** the repository now presents an evidence-driven progression—saturated fixture, harder
  benchmark, selected Pointwise ranker, calibrated abstention and deployment restraint—without
  changing code, data, models, thresholds or runtime behavior.

## D54 — Treat mining, domain ranking and calibration as one gated ML loop

- **Choice:** plan hard-negative mining, domain MiniLM fine-tuning and selective-prediction
  calibration as one ordered development milestone. Require purpose-specific data permission and a
  permanent denylist for the opened 53-positive and 20-negative holdouts before any adaptive work.
  Keep all outputs development-only and `runtime_eligible=false`.
- **Reason:** these stages are statistically dependent. Mined negatives define the ranker; the
  frozen ranker defines the score distribution; calibration and thresholds are meaningful only
  after that distribution stops changing. Implementing them independently would invite leakage,
  stale calibration and post-result threshold tuning.
- **Alternatives:** fine-tune immediately on the existing 153-row dataset; reuse the 53/20 results
  as a new final test; tune calibration first; launch Pointwise after a development improvement.
  Each alternative crosses an existing authorization/evaluation boundary or turns development
  evidence into an unsupported runtime claim.
- **10x alternative considered:** acquire a large rights-cleared marketplace corpus with independent
  exact-release adjudication, physically isolated final labels and production-shaped serving
  telemetry. That remains the stronger long-term program, but it is a separate data acquisition and
  authority project; this v1 milestone first proves a bounded local ML loop.
- **Most likely failure:** treat every high-ranking non-target release as a hard negative even when
  the query lacks year, series or identifier evidence. The design therefore holds ambiguous siblings,
  mines only train rows and requires explicit source-relative authority rather than learning forced
  distinctions.
- **Impact:** implementation may begin only with the governance/data Gate. Existing Pointwise,
  Listwise and balanced holdout evidence remain immutable historical baselines; success or failure
  of the new development model cannot alter FastAPI defaults without separate fresh-final and
  runtime owner Gates.

## D55 — Accept Path B only as owner-attested, local-only ML development

- **Choice:** accept the owner's Path B decision for the hash-bound 100-row positive development
  partition and the existing 52-row no-match development partition. Allow the positives to support
  family-safe splitting, one-shot hard-negative mining, local domain fine-tuning and ranker
  selection; restrict the no-match rows to their existing 32-row calibration-fit and 20-row
  threshold-selection uses. Keep raw rows, mined pairs and checkpoints local and Git-ignored.
- **Reason:** this unlocks a bounded AI-engineering experiment without silently expanding evaluation
  data into public training assets. The owner states that the sources were acquired through Google,
  but the catalog record still says access/republishing rights were not provided; the artifact must
  preserve both facts instead of converting an acquisition statement into a verified license claim.
- **Alternatives:** block all work until independent license evidence exists; treat all 153 positives
  and all 72 negatives as trainable; publish the fine-tuned weights. The first would prevent the
  requested local experiment, while the latter two would reuse opened tests and exceed the stated
  evidence/publication boundary.
- **10x alternative considered:** obtain a first-party or explicitly licensed corpus with documented
  ML-training and derived-weight redistribution rights, independent exact-release adjudication and
  a physically isolated final split. That remains the proper route for public weights or stronger
  external-validity claims, but it is outside this local development Gate.
- **Most likely failure:** describe `owner_attested_not_independently_verified` as rights-cleared or
  assume Google discoverability grants unrestricted reuse. The validator therefore records the
  unresolved source-rights state, prohibits public rows/weights and binds all permissions to exact
  hashes and counts.
- **Impact:** DRSP-T1 may pass, but it starts no training. The 53 positive test rows and 20 negative
  holdout rows are permanently denied from every adaptive phase. DRSP-T2 and later tasks still need
  their own owner Gate, and fresh final evaluation/runtime activation remain unauthorized.

## D56 — Amend T1 with artifact-specific public release Gates

- **Choice:** preserve the byte-identical T1 authorization and governance as the historical
  decision, then add a T1A publication amendment plus effective governance v2. A minimized,
  versioned row-level hard-negative pair package and the actual safetensors checkpoint may be
  Git-tracked or publicly released only after their respective release Gates pass. Fresh-final
  aggregate reports and runtime code/config/model manifests may also be public in later phases,
  while final execution, runtime activation, a public endpoint and row-level final data remain
  separately gated. The rights state remains `owner_attested_not_independently_verified`.
- **Reason:** publication eligibility is different from artifact creation, evaluation execution and
  runtime activation. A versioned amendment records the Owner's correction without rewriting T1 as
  though the broader permission had existed originally. The v2 effective view gives downstream
  validators one current policy while retaining both T1 hashes as an auditable chain of custody.
- **Alternatives:** overwrite the T1 JSON; stop ignoring the whole milestone tree; commit every run
  output; or keep every pair/checkpoint private. Overwriting would erase decision history, broad
  unignore rules could leak scratch or final rows, committing all outputs would bypass release
  review, and permanent privacy would contradict the Owner's corrected publication intent.
- **10x alternative considered:** publish a complete model package through a registry with signed
  provenance, SBOM attestations, reproducible training infrastructure, automated privacy/license
  scans and staged endpoint deployment. That is stronger supply-chain evidence, but it depends on
  artifacts and evaluations that do not yet exist; T1A establishes the smaller enforceable contract
  first.
- **Most likely failure:** interpret an allowlisted path as proof that its contents are already safe
  or released. The first QA pass also found that ignoring only named local directories was not
  default-deny: arbitrary files under the milestone data directory could become trackable. The
  correction ignores the entire milestone data and artifact trees, then allowlists only the four
  governance JSON files, the named public pair package and the named public checkpoint package.
  Their release-state fields still begin false and must fail closed on unexpected content.
- **Impact:** DRSP-T1A is complete, but no pair package or checkpoint has been published. Fresh-final
  state remains `evaluation_authorized=false` and `executed=false`; runtime state remains
  `activation_authorized=false` and `activated=false`. The 53/20 denylist, T1 file/content hashes,
  runtime default and public endpoint status remain unchanged. DRSP-T2 still requires its own Owner
  Gate.

## D57 — Freeze query-only Top-25 pools before mining and expose the calibration shortfall

- **Choice:** complete DRSP-T2 by grouping the 100 admitted positive development rows with connected
  components over normalized query, alias, evidence event, casting family and exact identity, then
  assigning whole components through deterministic salted ordering to a 70-row ranker-train and
  30-row ranker-selection split. Freeze one query-only RRF Top-25 pool per row and score each pool
  once with the revision-pinned generic MiniLM. Keep row-level assignments and scored candidates in
  Git-ignored mode-`0600` local artifacts; publish only three mode-`0644` aggregate manifests.
- **Reason:** mining must not choose its own split or see expected targets during retrieval. Connected
  components make every declared leakage relationship an indivisible unit; salted ordering makes the
  result reproducible without exposing membership. Query-only retrieval followed by target
  observation measures real retrieval misses, while target injection would convert Recall@25 into a
  guaranteed result. Binding catalog, retriever, renderer, code, model revision, config and manifest
  hashes keeps the future generic/domain comparison on identical inputs.
- **Alternatives:** random row splitting; stratify or inject by expected identity; rebuild pools after
  fine-tuning; include the 53 opened test rows to increase sample size; publish row-level split and
  scores. These alternatives respectively permit family leakage, inflate retrieval recall, make the
  baseline incomparable, reuse opened final evidence or disclose private development data.
- **10x alternative considered:** build a larger independently collected, rights-cleared and
  family-balanced corpus with physically isolated ranker, calibration and fresh-final partitions,
  then publish signed provenance for every pool. That would remove the present small-data and
  calibration-capacity constraints, but it is a separate acquisition program rather than the
  smallest honest gate before one-shot mining.
- **Most likely failure:** the expected identity leaks into retrieval indirectly, making every pool
  look successful. The first QA pass therefore required both an exact 70/30 assertion and a retrieval
  spy plus mutated-target invariance test. After the fix, changing the expected target cannot change
  the retrieved candidate sequence; all 100 pools contain 25 candidates, with zero target injections
  and zero retrieval misses. A smaller deferred risk remains: public-only validation checks artifact
  schema and self-checksums but cannot rederive row-level aggregate claims without the private files.
- **Impact:** T2 is PASS with 100 singleton components and zero family, exact-identity, normalized-
  query, alias or evidence overlap. The 53-row positive test file bytes are parsed as part of the
  153-row source before filtering, but test adaptive use/scoring and 20-row negative-holdout/no-match
  ranker scoring remain zero. Mining, training, calibration, final evaluation and runtime actions
  remain zero. T6 now has an explicit shortfall of zero available family-disjoint catalog-present
  calibration rows; that shortfall does not block a separately authorized T3 train-only mining run.

## D58 — Release one fixed hard-negative package and keep ambiguous siblings out of binary truth

- **Choice:** complete DRSP-T3 with one deterministic mining pass over only the 70 `ranker_train`
  queries and their byte-unchanged T2 Top-25 pools. Release exactly five files containing 345 binary
  pairs: 207 adjacent-year/wrong-series-or-identifier, 67 same-casting wrong-exact, 67 high-generic-
  score and 4 high-RRF negatives. Require at least two negatives for 36 queries and at most five per
  query; the result reaches 69/70. Hold 65 ambiguous same-family candidates rather than force them
  negative, and exclude or hold 45 permanent-holdout identities, 34 selection identities and 20
  candidates without explicit target-casting evidence.
- **Reason:** the training artifact must teach difficult distinctions without converting proximity
  into false certainty. A one-shot pass against frozen generic pools isolates mining from future
  domain-model errors; explicit evidence rules and holds preserve label semantics. The fixed
  five-file release contract makes the publication exception auditable instead of allowing an
  arbitrary directory tree into Git.
- **Alternatives:** label every non-target Top-25 candidate negative; iteratively remine after each
  fine-tuning run; include selection, opened test, no-match or permanent-holdout rows; keep the pairs
  private despite Owner permission; or allow any nested file below the public package path. These
  choices respectively introduce false negatives, adaptive feedback, leakage, contradict the
  release decision or create an uncontrolled disclosure surface.
- **10x alternative considered:** build a much larger independently licensed catalog-query corpus
  with expert graded-relevance labels, multiple negatives per evidence dimension, signed provenance
  and reproducible secure-build attestations. That would improve label coverage and external validity,
  but it is a separate acquisition program; the current package is the smallest honest artifact for
  testing whether domain fine-tuning adds value over the pinned generic cross-encoder.
- **Most likely failure:** treat same-family siblings as automatically wrong, or interpret the
  released package as manufacturer-certified truth. The miner therefore holds ambiguous siblings,
  retains the `owner_attested_not_independently_verified` limitation and states that training
  membership is intentionally revealed. Two QA/security rounds also replaced a broad nested
  allowlist with exact recursive five-file enforcement, expanded AWS/Bearer/`.env`/path-traversal/
  contact scans, avoided false-positive rejection of valid 11-digit barcodes, rescanned the final
  manifest and applied the denylist to sanitized content.
- **Impact:** `pairs.jsonl` SHA-256 is
  `50f88e73889b31e8f314e93b2cca9e4871934662b5218c6659a72fe06c0ca2ba`, package SHA-256 is
  `89bc430289c36e75c6302e7aa4ecca1889f32df95e5199f61aba1f676b18022a`, and manifest content
  SHA-256 is `da5422568c9b0bae6e3d152d66318e251329ca966dbdff078a78029c77a04392`.
  The 30 selection, 53 positive-test, 20 negative-holdout and 52 no-match rows received zero mining
  and zero scoring; the T2 pool bytes did not change. Training, checkpoint creation, calibration,
  final evaluation and runtime activation remain zero. T4 requires a separate Gate plus an exact
  checkpoint-package allowlist, and untrusted text must never reach `eval`, a shell or prompt
  interpolation.

## D59 — Publish two early-stopped domain MiniLM checkpoints without selecting a winner

- **Choice:** execute DRSP-T4 with one frozen binary Pointwise recipe and seeds 17/29, use only the
  30-query T2 selection partition for per-seed early stopping, and publish both epoch-1 checkpoints
  as float16 safetensors after the exact package Gate passes. Keep generic/domain comparison and all
  winner logic in T5.
- **Reason:** two seeds test whether the optimization direction is stable, while selection-only
  early stopping limits small-data overfitting. Both runs reduced training loss through epoch 3 but
  achieved their best MRR@10 at epoch 1, so retaining the lower-loss later epochs would optimize the
  wrong signal. Publishing both checkpoints preserves T5's fair comparison rather than choosing the
  more favorable seed after seeing downstream metrics.
- **Alternatives:** train one seed; search objectives/hyperparameters; retain the lowest-loss epoch;
  use opened holdouts for early stopping; publish float32 90 MB blobs; or declare the common MRR a
  winner now. These respectively weaken stability evidence, create a small-data model zoo, overfit
  train loss, leak final evidence, create oversized Git blobs, or collapse T4/T5 Gates.
- **10x alternative considered:** use a larger independently licensed and family-balanced corpus,
  distributed reproducible training, signed SBOM/provenance and an external model registry with
  independent final evaluation. That would support stronger public-model claims, but it is outside
  the bounded portfolio experiment and does not justify weakening the current holdout boundary.
- **Most likely failure:** confuse early-stopping MRR with proof that the domain model beats the
  generic model. The model card and AI-eval therefore label winner quality `not evaluated`; T5 must
  score generic and both domain seeds on identical frozen pools with preregistered quality, latency
  and stability gates.
- **Impact:** both seeds select epoch 1 at MRR@10 `0.86111111` and stop at epoch 3. Checkpoint hashes
  are `652f1e900bfeefd1536603e2d7e3b9c783df7b93273eb0a83a3bb0dce4360417` and
  `315df109e64798108cb06fb249cb43f85f625e8224f34b51559b8d4c74cecb2d`; package SHA-256 is
  `1cc26cc8aea072d02cb5fd25909b0adfcdbdfd2a7f642433945cf00211b002e1`. Two clean rebuilds match
  byte-for-byte. The 53/20 holdouts and 52
  no-match rows remain unused, runtime unchanged, and T5+ unauthorized.

## D60 — Reject both domain checkpoints when the frozen selection gate fails

- **Choice:** run DRSP-T5 once on the identical 30×25 T2 selection pools with the pinned generic
  MiniLM and both released T4 checkpoints, then publish `winner: null`. Do not calibrate either
  domain checkpoint or reinterpret the common seed result as stability success because neither seed
  improves in the required direction.
- **Reason:** the value of domain fine-tuning must be established against the generic baseline, not
  inferred from falling training loss or early-stopping scores. Generic reaches exact Top-1 `24/30`,
  MRR@10 `0.87777778` and same-family accuracy `41/52`; both domain seeds reach `23/30`,
  `0.86111111` and `40/52`. Both also exceed the absolute 200 ms CPU p95 budget. The preregistered
  all-or-nothing gate therefore has no eligible checkpoint.
- **Alternatives:** choose seed 17 because its measured p95 is slightly lower; treat equal two-seed
  metrics as sufficient stability; relax the exact/MRR/hard-negative thresholds; or move directly
  to calibration. Those choices optimize after seeing the result, confuse consistent regression
  with positive stability, or attempt to hide ranking failure behind probability calibration.
- **10x alternative considered:** obtain a materially larger, independently rights-cleared and
  family-balanced query corpus, mine graded same-family negatives, pretrain on broader catalog
  language and run nested development/model-selection partitions before a fresh final test. That is
  a new experiment and data program, not a repair that may be applied to this frozen result.
- **Most likely failure:** present the existence of fine-tuned checkpoints as evidence that they are
  better. README and AI-eval evidence therefore separate pipeline capability from model quality and
  explicitly state that no domain ranker is selected.
- **Impact:** T5 result content SHA-256 is
  `d9665b151c4c3263afd8e24345024985904f1a407d93ce6c9173ed37d8444e2b`; public file SHA-256 is
  `219789db3f1e6f7e3e114656d165ca3ebe733225139e294787dc64beaa3e25c3`. Casting Top-1 and Recall@25
  remain `30/30` for all arms, but exact, MRR and same-family metrics regress. Positive test,
  negative holdout and no-match development reads/scores remain zero. R9 blocks T6 because there is
  no selected checkpoint hash; final evaluation and runtime remain unauthorized.

## D61 — Start a new pairwise remediation spec instead of calibrating the failed v1 ranker

- **Choice:** close the v1 feedback loop at `winner: null` and draft a separately governed v2 that
  requires at least 180 new queries, independent train/validation/selection partitions, denser
  same-casting evidence and one fixed pairwise ranking objective. Keep the 200 ms latency budget, but
  require generic environment readiness before spending labels or training compute.
- **Reason:** both seeds regress in the same way, both peak at epoch 1, and later lower training loss
  corresponds to worse MRR. Only 67/345 v1 negatives are same-casting wrong-exact, while 65
  same-family candidates were held. This makes data density and objective alignment defensible
  hypotheses. Calibration cannot repair ranking, and reusing observed T2 errors would be adaptive
  leakage.
- **Alternatives:** calibrate seed 17; lower the v1 gates; add more epochs; remine from T5 errors; or
  start a Pointwise/Pairwise/Listwise sweep. These respectively promote a failed ranker, move the
  goalposts, intensify observed overfitting, leak selection evidence or create an underpowered model
  zoo.
- **10x alternative considered:** collect a large independently licensed marketplace-query corpus
  with graded multi-release relevance, expert adjudication, nested cross-validation and external
  final evaluation. That is the strongest route, but the proposed 180-query minimum is the smallest
  new experiment that separates early stopping from model selection and can test the pairwise
  hypothesis honestly.
- **Most likely failure:** synthesize many nominal rows without enough query-supported exact-release
  information. V2 therefore gates on at least 60 train queries with two defensible same-casting
  negatives each; row count alone cannot pass readiness.
- **Impact:** only planning task DRV2-T0 is complete. No data was collected, no v1 artifact changed,
  no model was scored or trained, and no downstream Gate was authorized. Owner approval of source,
  rights, split, objective, gates and publication remains mandatory.

## D62 — Govern owner-authored v2 queries from the frozen catalog without promoting source authority

- **Choice:** interpret the Owner's next-step instruction as DRV2-T1 approval only. Bind the frozen
  1,763-row community snapshot, exclude every identity from the existing 153-positive dataset and
  every query hash from the positive/negative holdouts, and freeze deterministic owner-authored
  templates. Publish only three aggregate governance files; defer row materialization to T2.
- **Reason:** the catalog has sufficient unused capacity—1,041 eligible rows across 269 multi-release
  families—without reusing observed selection errors. A protocol overlay can grant bounded project
  use while preserving the source's recorded staging status and the fact that rights were not
  independently verified.
- **Alternatives:** reuse the 100 v1 development queries; use the 53 opened positives; scrape another
  live source immediately; publish all authored rows; or silently treat staging data as canonical.
  These introduce adaptive reuse, holdout leakage, uncontrolled acquisition, unnecessary row-level
  disclosure or false authority.
- **10x alternative considered:** independently license and expert-review a new marketplace-query
  corpus with signed per-record provenance and exact-release adjudication. That remains the strongest
  route, but the bounded synthetic protocol is sufficient to test pipeline and pairwise-learning
  mechanics while preserving honest limitations.
- **Most likely failure:** confuse catalog capacity with valid training data. T1 therefore reports
  capacity only; T2 must still materialize, validate and partition 180 rows, and later density/mining
  Gates can fail even when source capacity is large.
- **Impact:** authorization, protocol and governance file SHA-256 values are respectively
  `d42ab9415c66c24b986731292ff9a9d02f4dd46a974b57c9cd0a4b3bfa8e3fab`,
  `9d56b2d2ad524159b5334b9b1a3aab321954e6153a3ae5afe5ca9935806be4fc` and
  `66bbe6f660492a372e2a7dce70ba126b849913efd25c952e389886dbc73ca3d6`.
  No queries, partitions, scores or models were created; T2 remains separately gated.

## D63 — Freeze one query per casting family before any v2 model access

- **Choice:** interpret the Owner's next-step instruction as DRV2-T2 approval only. Deterministically
  select 180 distinct eligible casting families, one exact release per family and one frozen query
  template per row; assign the ordered families to 120 train, 30 validation and 30 untouched
  selection rows. Keep the row-level pack local-only and publish aggregate manifests only.
- **Reason:** one-family-per-query is stricter and simpler than a general connected-component
  splitter for this corpus. It guarantees zero family leakage across partitions and leaves at least
  two eligible sibling releases for every train query without deciding yet which siblings are valid
  negatives.
- **Alternatives:** randomly split individual releases; put multiple releases of a family in
  different partitions; manually choose easy rows; or publish all authored data. Those options risk
  family leakage, selection bias or unnecessary disclosure.
- **10x alternative considered:** collect independently licensed real marketplace queries with
  expert exact-release adjudication and grouped nested cross-validation. That remains stronger
  external-validity evidence, but it is unnecessary for the current bounded pipeline experiment.
- **Most likely failure:** mistake sibling availability for a defensible hard-negative label. T2
  records 120 density-ready train families but creates zero candidate labels; evidence-gated mining
  remains a separate task after candidate-pool readiness.
- **Impact:** the local query-pack content SHA-256 is
  `149d7d867b9e270ffb805906aec64685d6823f11efcd68a59e9e74ba60134e6f`; all query, identity and
  family overlap counts are zero. Candidate scoring, mining, training, calibration, final evaluation
  and runtime activation remain unauthorized; T3 needs a separate Owner Gate.

## D64 — Preserve the 200 ms latency failure instead of lowering the v2 Gate

- **Choice:** complete DRV2-T3 by freezing all 180 query-only Top-25 pools and recording the generic
  CPU latency result as FAIL. Do not start T4 because p95 `217.699834 ms` exceeds the preregistered
  `200 ms` ceiling.
- **Reason:** retrieval itself is ready—4,500 candidates, zero misses and zero target injections—but
  the generic baseline still misses the product latency budget. Lowering the budget or proceeding to
  model training would hide an environment/runtime problem behind a modeling experiment.
- **Alternatives:** relax the SLO; benchmark fewer/easier queries; use selection metrics to justify
  proceeding; or train first and optimize later. These move the goalpost, bias the measurement,
  contaminate untouched selection or spend compute before the common baseline is deployable.
- **10x alternative considered:** build and benchmark a production inference service across multiple
  hardware classes with ONNX/CoreML/quantized backends, concurrency load and statistical confidence
  intervals. That is valuable later; the smallest honest next step is one frozen CPU implementation
  repair with exact score/order equivalence on these pools.
- **Most likely failure:** optimize latency by changing logits or candidate ordering, making the
  later generic/domain comparison incomparable. T3R must therefore bind unchanged weights,
  tokenizer, inputs and Top-25 pools and prove equivalent ordering before accepting timing results.
- **Impact:** candidate-pool and latency content hashes are
  `da419555a6e364063a288a7ece691a330f849d361b7735809e616af4d4310777` and
  `7b396578d36e8c6a76fd79e447770713014716aa911661f4055898f2f0c76d86`.
  No labels, training, calibration, selection evaluation or runtime activation occurred. T4 is
  blocked; T3R needs a separate Owner Gate.

## D65 — Use float32 ONNX only after full-pool ordering equivalence

- **Choice:** repair DRV2-R8 by exporting the pinned generic safetensors checkpoint to float32 ONNX
  opset 17, then require `≤2e-5` maximum logit delta and identical complete Top-25 ordering on all
  180 pools before accepting the repeated latency benchmark. Keep the 91 MB graph local-only and
  publish its exact hash plus reconstruction dependencies.
- **Reason:** direct Transformers and SDPA diagnostics remained around the failed latency range, and
  `torch.compile` was not portable in the workspace path. Float32 ONNX preserves the model decision
  while applying inference-graph optimization; the formal run achieved 180/180 ordering identity
  and p95 `103.654042 ms` without changing weights or the 200 ms Gate.
- **Alternatives:** raise the latency budget; accept another PyTorch rerun; use dynamic INT8; commit
  the 91 MB graph; or activate ONNX directly in FastAPI. INT8 was specifically rejected because a
  diagnostic preserved only 3/180 complete orderings despite a smaller graph and passing latency.
  The other alternatives hide the failure, bloat the repo or expand runtime scope.
- **10x alternative considered:** benchmark signed ONNX/CoreML/TensorRT packages across several CPU
  classes under concurrent service load, with reproducible containers and confidence intervals.
  That belongs to productionization; the present repair answers the narrower experiment-readiness
  question.
- **Most likely failure:** call a faster but numerically different backend “the same model.” T3R
  therefore evaluates every one of the 4,500 frozen logits and complete within-pool order, rather
  than comparing only aggregate accuracy or a few smoke cases.
- **Impact:** maximum absolute logit delta is `1.4781951904296875e-05`; p95 improved by
  `114.045792 ms` (`52.39%`) to `103.654042 ms`. Result content SHA-256 is
  `f95095a1f710fedc5c8d98a2d1e72b7fda25b2d3a3c3edeaa3f5b469850b47f7`. T4 is now eligible for a
  separate Owner Gate, but no mining, training or runtime activation occurred.

## D66 — Require query-supported conflicts before a sibling becomes a v2 negative

- **Choice:** interpret the Owner's next-step instruction as DRV2-T4 approval only. Mine only the
  120 train pools. Admit a sibling only when it shares the normalized casting and conflicts with an
  exact-release field supported by that row's frozen query template; require two admitted siblings
  per query and hold everything ambiguous or below density.
- **Reason:** a different UUID proves only that two catalog rows differ. It does not prove the query
  contains enough evidence to prefer one release. Template-specific conflicts connect each binary
  preference to information actually visible to the ranker, while the two-negative threshold
  prevents nominally large but shallow training coverage.
- **Alternatives:** label every same-casting UUID as negative; use generic score/rank as pseudo-label
  authority; include one-negative queries; or inspect validation/selection to increase yield. These
  create unsupported labels, train the model to reproduce its own baseline, weaken the preregistered
  density rule or leak protected partitions.
- **10x alternative considered:** have independent experts adjudicate graded relevance for every
  release in each train pool using manufacturer records and inter-rater agreement. That would give
  stronger truth and richer listwise supervision, but it exceeds the bounded portfolio experiment;
  the present evidence rule is reproducible and honest about community-catalog limits.
- **Most likely failure:** call 332 generated triples a model improvement. The public manifest and
  AI-eval evidence therefore report training runs and selection evaluations as zero and keep T5
  separately gated.
- **Impact:** 112/120 train queries qualify and produce 332 triples. Nineteen ambiguous siblings and
  eight siblings from one-negative queries remain held. The local content SHA-256 is
  `5855d753b5567f0659f32ab685d68bf01277a3f4d99c62dbfd83024f2ef32411`; public manifest content
  SHA-256 is `2c4334db61f1d448290f36ab657909f66e6ee3ace263a92a075d8101434fca6b`.
  No validation/selection labels, training, calibration, final evaluation or runtime were used.

## D67 — Freeze one RankNet-style recipe before v2 validation is visible

- **Choice:** interpret the Owner's next-step instruction as DRV2-T5 approval only. Use
  `mean(softplus(-(positive_logit-negative_logit)))` with fixed seeds 17/29, learning rate `1e-5`,
  at most four epochs and validation-MRR@10 early stopping. Publish only float16 safetensors and an
  allowlisted support package; keep selection completely unread until T6.
- **Reason:** T4's supervision expresses an ordering—one release should rank above a sibling for the
  same query—so optimizing the score difference is closer to the resolver objective than two
  independent binary losses. Logistic loss avoids adding an ungrounded margin hyperparameter, and
  the lower learning rate responds prospectively to v1's epoch-one overfitting without consulting
  any v2 validation result.
- **Alternatives:** reuse BCE pointwise training; search pairwise margin values; compare Pointwise,
  Pairwise and Listwise objectives; or use selection for early stopping. These either repeat the v1
  mismatch, add a small-data hyperparameter search, create a model zoo or leak the final v2 choice
  partition.
- **10x alternative considered:** pretrain a larger domain encoder on independently licensed product
  text, then run nested cross-validation across multiple ranking objectives with expert graded
  relevance. That could improve generalization, but it answers a broader research question than the
  fixed pairwise remediation hypothesis.
- **Most likely failure:** validation improves for one seed but untouched selection does not. T5
  therefore releases both reproducible checkpoints without a winner claim; T6 alone may compare
  them with generic under frozen qualification gates.
- **Impact:** code, recipe and package contract are committed before training. T5 may read only 332
  train triples and 30 validation pools. Selection, holdouts, calibration, final evaluation and
  runtime remain prohibited.

## D68 — Release both T5 checkpoints without naming a winner

- **Choice:** publish the two successfully trained float16 safetensors checkpoints and their
  aggregate validation histories, but leave `generic_vs_domain_winner_selected=false`. Keep T6 as a
  separate one-shot selection Gate.
- **Reason:** both seeds reach validation MRR@10 `0.95`, but validation is an early-stopping signal,
  not independent evidence that either domain model beats generic. Publishing both preserves
  reproducibility and lets T6 apply predeclared qualification without retroactively choosing the
  nicer validation trajectory.
- **Alternatives:** select seed 17 because it reaches `0.95` one epoch earlier; select seed 29 because
  its final loss is lower; average weights; or run selection immediately. These confuse validation
  efficiency or training loss with final ranking quality, introduce a new unregistered model, or
  bypass the T6 Gate.
- **10x alternative considered:** repeat training across many seeds and nested folds, then ensemble
  only models with stable out-of-fold gains. That is statistically stronger but would change the
  preregistered two-seed experiment and consume substantially more compute.
- **Most likely failure:** both seeds look stable on validation but regress on untouched selection,
  as v1 did. The release manifest therefore makes no improvement claim and records selection reads
  and model-selection runs as zero.
- **Impact:** seed 17 selected epoch 2 with checkpoint SHA-256
  `5a4f2ea21b93a864f1e1ddb54523f68a0ae2766db555535c0f35721588b6e297`; seed 29 selected epoch 3
  with SHA-256 `83db9ab75c1c431ce2c6f3e4c717bae821c187a060f0864e45204ee8a4056e99`.
  Package SHA-256 is `28977b447a3ec7b7fa970d7c5eec8ce3b0a2c5f33b4c50c3dbd6dfca7dbb7663`.
