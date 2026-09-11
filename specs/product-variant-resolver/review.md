# Product Variant Resolver — Lite MVP QA Review

> Date: 2026-09-01  
> Last focused update: 2026-09-11 (T47 family-level human-knowledge specification)
> QA mode: `.codex/agents/qa.toml` MVP Mode  
> Scope: `specs/product-variant-resolver/mvp-brief.md` R1–R30
> Verdict: **PASS WITH RISKS**

## Verdict summary

The dependency-light, offline fixture path is demonstrable and internally consistent. The original
38-test QA suite passed, and the later fresh constrained Python 3.12 host suite passed 41/41;
Python compilation, fixture validation, report regeneration, report disclosure validation, and
Docker Compose static configuration also passed. Manual API spot checks produced all three decision
states, omitted debug data by default, bounded debug candidates, and failed closed for missing
catalog and unavailable external model providers. T09 later verified the opt-in PostgreSQL sparse
backend and its own fail-closed cases.

The focused re-verification also confirms the three requested corrections: series knowledge is
derived from the catalog and a conflicting series remains a soft conflict; RRF is the default
runtime ranker based on a traceable frozen-test comparison showing zero Top-1 gain from the local
heuristic reranker; and the report contains warmed in-process HTTP/ASGI `/resolve` samples with an
explicit statement that container/TCP latency was not measured.

The T26–T28 data additions passed the current host suite **57/57**, including four corpus tests,
five alignment tests, and seven human-backed catalog tests. The fixture validator now includes the
auxiliary dataset, alignment, and draft-catalog checksums plus label/status/identity invariants;
Python compilation and `git diff --check` also pass. These tests validate the imported artifacts
and their boundaries, not canonical resolution accuracy on the newly imported names.

T29 executes an independent human-knowledge retrieval stage on every resolution request while
preserving the canonical catalog as the only final-identity authority. The current host suite passes
**64/64**. The reviewed BMW query ranks the expected provisional variant first but still returns
`no_match` and a null canonical UUID; missing or review-bypassing human catalogs fail closed; debug
results are bounded and omitted by default. This proves the dual-source execution and safety
boundary, not accuracy on unseen real-world queries.

T07 is now runtime-verified against an isolated PostgreSQL 16/pgvector database. The first import
created 120 products, 240 aliases, 120 identifiers, 120 provenance rows, 120 sparse-search documents,
and one metadata row. Repeating the import preserved every row exactly. A mid-import identity
collision and a 119-of-120 incomplete snapshot both rolled back without changing the accepted
catalog. That milestone closed persistence but did not, by itself, prove PostgreSQL retrieval.

T09 now connects the canonical sparse-retrieval boundary to PostgreSQL full-text search. An
isolated PostgreSQL 16.14 run recovered all 12 matched frozen-test targets within Top-25, returned
an exact identifier at Top-1, used the existing GIN index under a forced index-compatible plan, and
kept an injection-shaped title in bound parameters. The PostgreSQL-backed API passed both
in-process and real HTTP resolution, while a corrupted catalog checksum failed readiness with 503.
The host suite at that milestone passed **71/71**.

T10 now materializes the versioned 192-dimensional `hashing-v1` catalog vectors and performs exact
cosine-distance retrieval with pgvector. The isolated PostgreSQL 16.14 run stored 120/120 vectors,
proved identical repeated materialization, recovered a catalog alias plus all 12 matched test
targets within Top-25, and rejected an intentionally missing row at readiness. A real HTTP request
reported both PostgreSQL candidate sources ready and kept the expected Nomad identity first in
sparse, dense, structured, and fused ranks. The final host suite passes **77/77**. This verifies the
database vector lifecycle, not a neural embedding model.

T30 adds a revision-frozen, text-only intake path for external catalog expansion without weakening
the canonical-identity boundary. Two identified MediaWiki API requests captured the source license
and revision `790665`; the importer normalized exactly 100 rows from the 2025 list. Validation found
100 unique toy numbers, 45 explicit variant notes, 100 unknown colors, and zero canonical
promotions. The final host suite passes **79/79**. This proves repeatable staging and attribution,
not that these rows are canonical identities or that Wiki coverage is accurate enough for release.

T31 deterministically compares all 100 staged rows with both existing catalog layers at exact
brand/casting-family level. The 100 rows reduce to 53 distinct families: 9 rows / 4 families have
an exact human-backed candidate, 91 rows / 49 families have no exact candidate, and none match the
synthetic canonical fixture. All 100 decisions remain held with null canonical identity. Five new
tests bring the complete host suite to **84/84**; the check command reproduces both frozen outputs
byte for byte. This is conservative pre-review evidence, not completed human adjudication.

T32 makes the remaining human work explicit and auditable. It groups all 100 source rows exactly
once into 53 stable family decisions, orders the 4 exact existing-family candidates before the 49
research-required groups, and produces both JSON and a readable Markdown worksheet. All reviewer
fields remain empty, all decisions remain pending, and promotion eligibility is zero. Five focused
tests bring the complete host suite to **89/89**. This passes queue preparation, not human review.

T33 prepares the first four decisions without filling them. The deterministic evidence packet puts
nine Wiki rows beside four retained human labels, their initial source names where available,
structured series/variant values, source case IDs, and exact target family IDs. All four receive a
machine family-merge recommendation and a separate variant hold. Subaru exposes a shared `zamac`
token but remains unverified at variant level. Five tests bring the host suite to **94/94**. This
passes evidence preparation, not reviewer confirmation or promotion.

T34 records the project owner's follow-up authorization as a separate, attributable decision batch
and derives a new adjudicated queue without editing the original. Four exact-target family merges
are completed, 49 family decisions remain pending, all nine affected Wiki release variants remain
held, and promotion eligibility stays zero. An invalid target fails closed. Five tests bring the
host suite to **99/99**. This passes family-decision recording, not canonical or variant promotion.

T35 researches the first ten pending priority-2 families in queue order. Dedicated Wiki casting
pages are checked against exact-name evidence from at least one non-Fandom publisher. Nine families
meet the source rule for a machine `create_new_casting` recommendation; `'55 Chevy` remains held
because its title disambiguates 1982, 1998, and 2006 casting tools. Six focused tests bring the host
suite to **105/105** and prove deterministic order, hashes, same-host rejection, pending reviewer
state, variant hold, and zero promotion. This passes bounded research, not owner adjudication or
catalog/database creation.

T36 records the owner's follow-up approval in a separate decision file and applies it to a copy of
the T34 cumulative queue. Nine new-family decisions and the `'55 Chevy` hold are completed, while
the four earlier merges and both decision-batch records remain intact. The queue now reports 14
completed / 39 pending families and 28 held release variants, with zero promotion eligibility.
Six focused tests bring the host suite to **111/111**; changed outcomes and incomplete batches fail
closed. The first focused run exposed only a test fixture's incorrect expectation for the prior
batch ID; it was corrected to the existing stored ID and the full rerun passed.

T37 continues from the T36 cumulative queue rather than re-reading the original all-pending queue.
It selects the next ten pending priority-2 families / eighteen Wiki rows. Nine dedicated casting
pages have a non-Fandom exact-name confirmation and receive machine `create_new_casting`
recommendations. `Batman and Robin Batmobile` stays held because a separate 2004 100% Hot Wheels
casting uses the same display name. Six new tests bring the host suite to **117/117** and prove
cumulative selection, two-host evidence, the homonymous-tool hold, pending reviewer state, variant
hold, zero promotion, frozen hashes, and deterministic reproduction of both research batches.

T38 records the owner's follow-up authorization in a separate batch-02 decision file and applies
it to a copy of the T36 cumulative queue. The nine creation recommendations and Batman hold become
completed family decisions while all eighteen batch-02 release rows remain variant-held. All three
earlier/current decision events remain ordered. The resulting queue reports 24 completed / 29
pending families, 4 merges, 18 accepted new families, 2 holds, 46 held release rows, and zero
promotion. Six new tests bring the host suite to **123/123**; changed outcomes, incomplete coverage,
history loss, hashes, and deterministic reproduction are covered.

T39 continues from the T38 cumulative queue and selects the next ten pending priority-2 families /
eighteen Wiki rows. All ten dedicated casting pages have a non-Fandom exact-name confirmation and
receive machine `create_new_casting` recommendations. The packet retains Fiat 500 as a separate
lineage from Fiat 500e and the older `'51 Merc` as a differently named predecessor to the newer
Hirohata Merc, without treating either relation as a same-name homonym. Six new tests bring the
host suite to **129/129** and prove cumulative selection, two-host evidence, related-tool
distinctions, pending reviewer state, variant hold, zero promotion, frozen hashes, and deterministic
reproduction of all three research batches.

T40 records the owner's follow-up authorization in a separate batch-03 decision file. All ten T39
creation recommendations become completed family-only decisions while their eighteen release rows
remain variant-held. The derived queue preserves the prior twenty-four decisions and all four
ordered owner events, reporting 34 completed / 19 pending families, 4 merges, 28 accepted new
families, 2 holds, 64 held release rows, and zero promotion. Six new tests bring the host suite to
**135/135**; changed outcomes, incomplete coverage, reused batch IDs, history preservation, hashes,
and deterministic reproduction are covered.

T41 continues from the T40 cumulative queue and selects the next ten pending priority-2 families /
twenty-three Wiki rows. Eight dedicated casting lineages have non-Fandom exact-name confirmation
and receive machine creation recommendations. Mazda MX-5 Miata remains held because distinct 1991
and 2025 1:64 tools share the display name. Nissan Skyline 2000GT-R LBWK remains held because the
regular and Tooned same-scale tools share its name, even though HYW79/HYY30/HYX54 map to the Tooned
page. Six new tests bring the host suite to **141/141** and cover queue sequencing, two-host
evidence, tool/scale/retool boundaries, pending reviewer state, variant hold, zero promotion,
hashes, and deterministic reproduction of all four research batches.

T42 records the owner's exact eight-create/two-hold authorization in a separate batch-04 decision
file. The derived checkpoint preserves all thirty-four earlier completed decisions and appends the
ten current outcomes, reporting 44 completed / 9 pending families, 4 merges, 36 accepted new
families, 4 holds, 87 held release rows, and zero promotion. Six new tests bring the host suite to
**147/147**; altered outcomes, incomplete coverage, reused batch IDs, widened variant scope,
history preservation, hashes, and deterministic reproduction of all four checkpoints are covered.

T43 selects all nine families still pending after T42 and covers their thirteen Wiki release rows.
Six dedicated single-casting lineages receive machine creation recommendations. Nissan Skyline
GT-R (BNR32) is held for a separate same-scale RLC tool, Power Wheels Dune Racer is held as a
renamed Bogzilla release, and Standard Kart is held because one page spans character-bearing and
driverless tools. Six new tests bring the host suite to **153/153** and cover the exact final size,
new evidence classes, two-host creation evidence, pending reviewer state, variant hold, zero
promotion, hashes, and deterministic reproduction of all five research batches.

T44 records the owner's exact six-create/three-hold authorization in a separate batch-05 decision
file. The cumulative queue preserves all forty-four earlier decisions and appends the final nine,
reporting 53 completed / 0 pending families, 4 merges, 42 accepted new-family decisions, 7 holds,
100 held release rows, and zero promotion. Six new tests bring the host suite to **159/159** and
cover exact authorization scope, all six history events, family-only decisions, unchanged variant
hold, frozen hashes, deterministic reproduction, and fail-closed altered/incomplete/duplicate/
widened inputs. This closes review questions, not catalog or database materialization.

T45 specifies the next boundary without changing code or data. Thirteen EARS requirements define a
separate family-only registry with 42 stable new entities, 4 links to existing human-backed
families, 7 explicit hold exclusions, and all 100 source rows retained only as held release
references. The design deliberately rejects placeholder variants and display-name-based identity,
uses UUIDv5 over the immutable family review ID, and defers Dual-RAG/PostgreSQL integration. Static
source analysis confirms the 79 create / 9 merge / 12 hold row split, no exact-name collision between
the 42 creations and 97 existing human families, and no readable-ID collision within the accepted
set. The project owner confirmed this specification by requesting the next step.

T46 implements that contract as a separate deterministic registry. Forty-two accepted creations
now have stable UUIDv5 review identities, four merges point to exact existing human casting
IDs/UUIDs without minting duplicates, and seven holds remain auditable/non-indexable. All 100 source
rows occur exactly once as held release references; provisional variant, canonical promotion,
runtime-indexed family, and PostgreSQL counts are zero. Nine focused tests bring the complete host
suite to **168/168** and cover hashes, IDs, aliases, provenance, target resolution, hold exclusion,
row coverage, non-mutating checks, and fail-closed invalid inputs.

T47 specifies how those family identities may enter the second RAG without becoming variants or
canonical candidates. A separate 42-document runtime projection keeps the T46 audit registry
immutable, while a discriminated union combines it with the existing 100 provisional-variant
documents in one proposed v2 hybrid index. Read-only simulation over the actual 142-document pool
found globally unique UUIDs, recovered all 42 exact brand/name family queries within Top-5 (worst
rank 2), and retained the existing BMW regression at Top-1. It also exposed that shared tokens can
surface an unrelated family for a held-name query, which is why T48 independent evaluation remains
mandatory. No implementation changed, so the executable suite remains **168/168**.

An independent Docker runtime milestone now verifies the existing
`product-variant-resolver:lite` image on Docker Desktop 29.5.3/aarch64: Python 3.12.14, non-root
user `pvr` (UID 100), read-only root filesystem, writable tmpfs only, loopback-only published port,
healthy readiness, UI assets, all three decision states, and missing-catalog fail-closed behavior.
The checked-in host-to-container latency artifact is arithmetically traceable: 50 sequential raw
samples after 10 warm-ups produce nearest-rank p95 `4.721208 ms`.

Focused re-verification closed the prior runtime reporting dependency finding. `httpx2>=2,<3` is a
reasonable runtime dependency because the shipped `pvr-report` CLI directly uses FastAPI
TestClient. The selective Python 3.12 constraints freeze the compatibility-sensitive web stack,
remove legacy `httpx`, and hold AnyIO at 4.14.0 to avoid the alias warning exposed by AnyIO 4.15.1
with Starlette 1.6. A no-cache rebuild resolved the complete selected set and, in the rebuilt
read-only image, `pvr-report` generated JSON, Markdown, and four SVGs successfully.

T04 is now QA-closed as **PASS**. An isolated PostgreSQL 16/pgvector run completed the empty →
upgrade `0001` → downgrade `base` → upgrade `0001` cycle and compared both upgraded schemas. The
follow-up runner now proves index table/name/method/ordered columns, complete foreign-key
source/target/delete behavior, and the full normalized release-year check expression; Alembic's
script location is absolute. A sentinel application table caused the runner to refuse execution,
closing the prior safety-check concern. T07 separately verifies fixture ingestion, T09 verifies the
PostgreSQL FTS query adapter, and T10 verifies versioned exact-vector query execution.

This is not a full verification of every technology named in the MVP brief. PostgreSQL sparse and
exact dense resolution are verified with deterministic `hashing-v1`, while external neural
embedding/cross-encoder models remain explicitly deferred.
The Docker latency evidence is from one local arm64 machine over loopback with concurrency 1; it
does not cover TLS, a reverse proxy, a remote network, concurrent load, or PostgreSQL. The committed
constraints are selective rather than a complete transitive lock; PostgreSQL extras and other
unlisted indirect/build dependencies can still resolve differently. These limitations must remain
visible in any portfolio or repository claims.

## Requirement coverage

| Requirement | Result | Evidence / limitation |
|---|---|---|
| R1 Canonical resolution | PASS | Manual `POST /resolve` check returned `matched`, UUID/slug/product, and bounded confidence; benchmark matched cases passed. |
| R2 Ambiguity | PASS | Manual fixture check returned `ambiguous`, null identity, and machine-readable reason `confidence_below_match_threshold`. |
| R3 Unknown entity | PASS | Manual fixture check returned `no_match`, null identity, reason `no_candidate_above_threshold`. |
| R4 Default minimization | PASS | Default response keys exclude `debug`, candidates, ranks, scores, and timings. |
| R5 Explainability | PASS | Debug response contains extracted signals, bounded candidates, sparse/dense/structured/RRF/reranker fields, conflicts/matches, model versions, and all component timings. It reports selected sparse and dense implementations, including PostgreSQL exact-dense artifact version. With the R11 default decision, reranker fields are null and metadata says `disabled`; opt-in mode populates them. |
| R6 Syntax/knowledge boundary | PASS (fixture path) | Generic catalog ingestion is idempotent and PostgreSQL-runtime verified. Structured alias/identifier source data is preserved, the full searchable catalog is checksummed, and catalog-derived color addition needs no product-specific branch. T09 moves only canonical sparse retrieval into PostgreSQL; the independent human-knowledge source cannot issue canonical identity. T30 verifies external Wiki intake only; human review and canonical promotion remain deferred. |
| R7 Soft conflicts | PASS | Catalog-derived `series_hints` is implemented without a product-specific branch. Manual and integration checks show a target with the wrong catalog series remains in the top 25 and records `series` in `structured_conflicts`; year/color retention and collector-number logic remain intact. |
| R8 Reproducible split | PASS | 100 cases; `split_seed=240901`; version `fixture-v1`; 14 families occur in exactly one split; train/dev access guards pass; test labels are recorded as untouched by training. |
| R9 Retrieval gate | PASS | Fresh offline evaluation, PostgreSQL FTS, and exact pgvector each achieved Recall@25 `1.0` on the same 12 matched test cases (gate `>=0.95`). |
| R10 Ranking gate | PASS | Fresh test evaluation: Top-1 `1.0`, hard-negative accuracy `1.0` (4/4). |
| R11 Reranker value | PASS (alternative) | On the same 12 matched frozen test cases, RRF Top-1 `1.0` and heuristic-v1 Top-1 `1.0`, absolute gain `0.0`. The versioned report therefore selects RRF and omits the heuristic from the default runtime, while retaining an explicit opt-in/ablation path. It states that no external cross-encoder was evaluated. |
| R12 Reliability gate | PASS | Precision `1.0`, false-match rate `0.0`, coverage `0.8333` on 21 synthetic fixture test cases. |
| R13 CPU smoke budget | PASS (limited scope) | Checked-in host-to-Docker loopback evidence has 50 sequential samples, 10 excluded warm-ups, K=25, and nearest-rank p95 `4.721208 ms` (gate `<=1500 ms`). That measurement remains offline-only. PostgreSQL exact retrieval passed sequential functionality checks, but database latency, concurrency, TLS/proxy, and remote networking were not measured. |
| R14 API validation | PASS | Blank, 501-code-point, unknown-field, and limit=26 requests return structured 422; malformed JSON returns 400; unsupported media type returns 415; no tracebacks exposed. |
| R15 Health/readiness | PASS WITH RISK | Missing catalogs and unavailable external providers fail closed. PostgreSQL startup verifies server/catalog state plus dense metadata and every expected UUID/version/checksum; catalog checksum corruption or one missing vector produces health 503, and retrieval-time database failure maps to 503. Health remains a startup snapshot, so post-startup loss is detected on retrieval. |
| R16 Quality gate | PASS | The latest host suite passes 168/168; fixture and Wiki-pilot validation, deterministic Wiki review/queue/evidence/five research batches/five priority-two decision checkpoints/review-family registry, Python compilation, default/PostgreSQL Compose configuration, and `git diff --check` pass. T04 migration, T07 ingestion, T09 sparse, and T10 exact dense retrieval passed isolated PostgreSQL 16/pgvector verification. Offline remains the default; PostgreSQL canonical sparse+dense is opt-in. |
| R17 Human-label provenance | PASS | `human-labeled-real-noisy-v1` contains 101 confirmed human labels, including 91 initial-name/human-name pairs and 10 explicit `no_candidate` failures. Four source rows marked excluded were not imported. The frozen manifest records source and dataset checksums, and the corpus declares that it is excluded from canonical-resolution accuracy, calibration training, and threshold selection until catalog IDs are assigned. |
| R18 Conservative catalog alignment | PASS | The deterministic alignment covers all 101 reviewed records and freezes the human dataset, catalog, and output checksums. It reports 0 canonical mappings, 2 exact brand/casting family-only matches, and 99 unmapped records. Every unresolved record retains null UUID/slug; fuzzy matching is disabled. |
| R19 Human-backed catalog draft | PASS | All 101 confirmed labels are preserved in 97 deterministic casting entities and 100 provisional variants. One exact structured duplicate merges while keeping both cases and aliases. Checksums and unique IDs validate, and every provisional variant remains `needs_canonical_review` and excluded from canonical responses and calibration. |
| R20 Dual-source retrieval boundary | PASS (Lite scope) | Every request executes canonical retrieval plus an independent human-knowledge sparse/dense/RRF retrieval stage. Only canonical candidates enter ranking, policy, and final identity. A reviewed BMW query returns the expected provisional suggestion in bounded debug output while the canonical result stays `no_match`/null; unknown text returns no human suggestion; missing or review-bypassing human data fails closed; default responses omit both debug candidate sets. |
| R21 Governed external catalog pilot | PASS WITH RISK | A single revision-frozen MediaWiki response produced exactly 100 text-only staging records with checksums, attribution, sequential source rows, unique toy numbers, null colors, null canonical UUIDs, and `needs_canonical_review` status. No images were requested and no staged row enters runtime retrieval. Source accuracy, canonical mapping, formal legal/security review, and 3,000-row behavior remain unverified. |
| R22 Conservative external-catalog review | PASS WITH RISK | All 100 staged rows were compared with both catalogs using exact normalized brand/casting keys. The frozen report includes candidate IDs, reasons, actions, and checksums; fuzzy, identifier-only, and automatic promotion are disabled. Every row stays held/null. The 4 matched and 49 unmatched families still require human adjudication. |
| R23 Attributable human-adjudication queue | PASS WITH RISK | All 100 source rows occur exactly once in 53 stable family items. Four exact-candidate families are priority 1 and 49 research-required families priority 2. Merge/create/hold/reject is the closed decision set; reviewer/time/reason/evidence are required. The immutable base queue remains all-pending; the derived adjudicated queue records four owner decisions. All families remain promotion-ineligible. |
| R24 Priority-1 family evidence | PASS WITH RISK | Four deterministic packets cover all nine priority-1 Wiki rows and retain the corresponding initial/human labels, structured fields, source IDs, and exact family targets. Family merge is recommended while all variants remain held and reviewer fields empty. The evidence is sufficient to ask the reviewer a bounded family question, not to claim the answer or promote data. |
| R25 Validated family-decision application | PASS WITH RISK | A separate attributable batch completes four exact-target family-only merges while preserving variant hold, zero promotion eligibility, and the immutable original queue. Missing/invalid target evidence fails closed and outputs are checksum-frozen. The decision provenance is the project owner's conversation follow-up rather than a signed external identity. |
| R26 Bounded new-family research | PASS WITH RISK | Batch 01 deterministically selects ten pending priority-2 families / nineteen Wiki rows. Nine dedicated casting pages have exact-name confirmation from a non-Fandom publisher; one disambiguated name is held. Source notes and outputs are checksum-frozen, same-host evidence is rejected, reviewer fields remain pending, every variant is held, and promotion remains zero. Remote sources can change and the recommendations still require owner adjudication. |
| R27 Validated priority-2 decision application | PASS WITH RISK | A separate project-owner batch covers all ten frozen research packets exactly once and agrees with their nine-create/one-hold recommendations. The derived queue preserves four earlier merges and both batch records, reports 14 completed / 39 pending families and 28 held variants, and keeps promotion zero. Changed outcomes and incomplete coverage fail closed. The approval is conversation-attributed rather than cryptographically signed, and accepted new families are not materialized catalog entities. |
| R28 Cumulative priority-2 research sequencing | PASS WITH RISK | Batches 02–04 each verify the latest cumulative queue and select the next ten still-pending families; batch 05 selects the exact final nine without padding. All five batches reproduce. The final packet adds six creation recommendations and three holds for homonymous, renamed-lineage, and multi-tool-page evidence. External sources can change, held tool lineages remain unresolved, and current research results remain unconfirmed machine recommendations. |
| R29 Cumulative priority-2 owner decisions | PASS WITH RISK | Five separate priority-2 owner batches cover their frozen packets exactly once and preserve the four earlier priority-1 decisions plus six ordered history records. The final queue reports 53 completed / 0 pending families and all 100 variants held, with zero promotion. Changed/incomplete/duplicate/widened batches fail closed. Approval remains conversation-attributed. T46 materializes accepted outcomes only in a separate review-family registry, not the human runtime or canonical catalog. |
| R30 Related-casting identity boundary | PASS WITH RISK | Batch 03 retains differently named predecessor context without false holds. Batch 04 separates same-name tools from continuous retools and scale-qualified products. Batch 05 additionally distinguishes renamed existing releases and pages containing multiple tools: Power Wheels/Bogzilla, Standard Kart, and the separate same-scale BNR32 RLC tool remain held. These text-source distinctions are not physical-tool verification. |

## Checked items and reproducible evidence

Executed from the project repository root:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
# Latest full host rerun: Ran 168 tests — OK
# Host Python 3.14.6 emitted the known legacy-httpx TestClient warning; the constrained
# Python 3.12 runtime was previously verified with httpx2 and warnings-as-errors.

python3 -m compileall -q src tests scripts migrations
# Result: exit 0

python3 scripts/validate_fixture_data.py
# Result: exit 0; fixture manifest validated

PYTHONPATH=src python3 -m product_variant_resolver.evaluation
# Fresh result: Recall@25 1.0; Top-1 1.0; hard-negative 1.0;
# precision 1.0; coverage 0.8333; false-match rate 0.0; pipeline p95 3.29 ms

PYTHONPATH=src python3 scripts/train_calibration.py --output-directory /tmp/<qa-dir>
# Result: calibration and dev-selected policy generated; test_labels_accessed=false

PYTHONPATH=src python3 scripts/generate_evaluation_report.py --output-directory /tmp/<qa-dir>
# Result: versioned JSON, Markdown, and four SVG artifacts generated;
# fresh warmed in-process HTTP/ASGI p95 2.45 ms; schema/derivation audit passed

docker compose config --quiet
docker compose --profile postgres config --quiet
# Result: both exit 0 (static configuration only)

python3 scripts/build_fandom_priority_two_research.py --batch 1 --check
python3 scripts/build_fandom_priority_two_research.py --batch 2 --check
python3 scripts/build_fandom_priority_two_research.py --batch 3 --check
python3 scripts/build_fandom_priority_two_research.py --batch 4 --check
python3 scripts/build_fandom_priority_two_research.py --batch 5 --check
# Result: all five frozen research batches are deterministic and current

python3 scripts/apply_fandom_priority_two_decisions.py --batch 1 --check
python3 scripts/apply_fandom_priority_two_decisions.py --batch 2 --check
python3 scripts/apply_fandom_priority_two_decisions.py --batch 3 --check
python3 scripts/apply_fandom_priority_two_decisions.py --batch 4 --check
python3 scripts/apply_fandom_priority_two_decisions.py --batch 5 --check
# Result: all five cumulative priority-two decision checkpoints are deterministic and current

python3 scripts/build_review_family_registry.py --check
# Result: 42 new review families, 4 merge links, 7 hold exclusions, 0 variants;
# registry, manifest, and report are deterministic and current
```

Docker/Python 3.12 runtime milestone:

```text
Image: product-variant-resolver:lite
Latest rebuilt image ID: sha256:e67d64e95abab329c901bdb5946f86962a09dc7217e2048a3b1c0568ec8b9d75
Docker server / architecture: 29.5.3 / aarch64
Container Python: 3.12.14
Runtime user: uid=100(pvr), gid=101(pvr)
ReadonlyRootfs: true
Published port: 127.0.0.1:8000 -> 8000/tcp
Compose state: healthy
```

- `/app` is not writable; `/tmp` tmpfs is writable.
- Container source/migration compile passed using `/tmp` as the bytecode cache.
- The prior runtime milestone's read-only mounted Python 3.12 runs passed 26 tests: 10 unit, 7 integration,
  4 evaluation metrics, and 5 fixture tests.
- That milestone's direct container evaluation remained green: Recall@25 `1.0`, Top-1 `1.0`, hard-negative
  accuracy `1.0`, precision `1.0`, coverage `0.8333`, false-match rate `0.0`; container pipeline
  p95 was `1.380833 ms` on this run.
- Real host-to-container HTTP returned health 200/ready; `/`, `/app.js`, and `/styles.css` returned
  200; `matched`, `ambiguous`, and `no_match` fixtures returned their expected states; the default
  response omitted debug fields and supplied `x-request-id`.
- A dedicated missing-catalog container returned health and resolve 503 without an identity and was
  removed immediately after the check.
- Compose logs contained normal startup, health, UI, and resolve access entries with no traceback or
  application error.
- `reports/runtime-validation/docker-python312-http-latency.json` has the exact expected v1 keys,
  50 finite non-negative raw samples, and matching min/median/mean/max. Sorting the samples and
  applying `ceil(0.95 * 50) - 1` reproduces p95 `4.721208 ms` exactly.
- Runtime latency evidence is single-machine arm64, loopback, sequential, concurrency 1, and offline
  memory only. It excludes TLS, proxying, remote networking, concurrent load, and PostgreSQL.

Focused dependency-contract and reporting re-verification:

- `pyproject.toml` now declares `httpx2>=2,<3` in runtime dependencies. This placement is justified
  because `pvr-report` is installed in the runtime image and calls FastAPI TestClient directly.
- `constraints/python312.txt` selectively fixes FastAPI `0.141.1`, Starlette `1.6.0`, httpx2
  `2.12.0`, httpcore2 `2.12.0`, AnyIO `4.14.0`, Pydantic `2.13.5`, and Uvicorn `0.52.4`.
  Legacy `httpx` was removed from the dev extra. A no-cache Docker build succeeded with this exact
  set; `python -W error` imported TestClient without warning and confirmed legacy `httpx` absent.
- Inside the rebuilt read-only/non-root container, `pvr-report --output-directory
  /tmp/qa-runtime-report` generated exactly: one JSON, one Markdown, `retrieval-ablation.svg`,
  `reranker-comparison.svg`, `precision-coverage.svg`, and `latency.svg`.
- The generated JSON passed `validate_report_payload`, used schema
  `pvr-evaluation-report-v2`, retained 21 HTTP samples, and preserved the exact 21-case synthetic
  non-production disclosure plus `container.measured=false`.
- Generated Markdown retained the non-production statement, no-external-cross-encoder statement,
  and container-latency-not-measured statement. All four SVGs contain `<svg>` and `<title>`.
- Rebuilt-image mounted tests: all 39 tests not requiring Node passed across backend, API,
  evaluation, reporting, integration, unit, and fixture scopes. The attempted full 41-test
  selection errored only at the UI controller test because the runtime image has no Node; the
  fresh constrained host environment is the 41/41 UI-inclusive evidence.
- Compose became healthy; inspection showed `User=pvr` and `ReadonlyRootfs=true`. Live health and
  three-state HTTP checks passed, and `ambiguous`/`no_match` returned no identity.
- The selective constraints are not a complete transitive lock. PostgreSQL extras and unlisted
  transitive/build dependencies remain range-resolved.

T04 PostgreSQL/pgvector migration verification:

- The existing `0001` migration required no schema change. In isolated Compose project `pvr-t04`
  on host port `55432`, PostgreSQL 16/pgvector passed empty → upgrade `0001` → downgrade `base` →
  upgrade `0001`; the first and second upgraded snapshots matched and final revision was `0001`.
- The strengthened runner verifies all seven application tables, primary/unique constraints, the
  complete normalized release-year expression, every required foreign key from its source column
  to `product_variant.canonical_uuid` with `ON DELETE CASCADE`, and each required index by table,
  name, method, ordered columns, and column order. It also verifies `tsvector`, `vector(192)`, and
  the installed `vector` extension. Its absolute Alembic `script_location` removes dependence on
  the caller's current directory.
- A sentinel application table present before invocation caused the runner to abort before any
  downgrade, closing the destructive-use safety finding. The guard checks existing application
  tables only; it does not inventory views, functions, custom types, or every possible schema
  object, so the runner remains restricted to a disposable database.
- The isolated container, network, and volume were removed after the checks. The responsible run
  also reported the host suite **41/41 PASS**, runner/migration Python compilation **PASS**, and
  `git diff --check` **PASS**. CI does not yet start PostgreSQL and execute this cycle automatically,
  and extension creation may require database-administrator permission.

Additional audit results:

- Fixture: 120 products, 100 benchmark cases (`60 matched`, `20 ambiguous`, `20 no_match`),
  14 casting families, and 30 near-duplicate groups.
- Frozen catalog and benchmark SHA-256 values match `data/manifest.json`.
- Existing report passes its schema, metric-derivation, and disclosure validator.
- Report clearly says it covers 21 synthetic fixture test cases and does not establish production
  accuracy, marketplace coverage, or production readiness.
- R7 manual evidence: a catalog-provided wrong series was extracted as `series_hints`; the expected
  target remained retrievable and carried `structured_conflicts=["series"]`.
- R11 evidence: RRF and heuristic-v1 both have Top-1 `1.0` on the same 12 matched test cases. The
  checked-in and freshly generated reports record absolute gain `0.0`, `selected_default="rrf"`,
  `heuristic_reranker_runtime_enabled=false`, and `external_cross_encoder_evaluated=false`.
- R13 evidence: fresh report generation retained 21 warmed HTTP/ASGI samples after five excluded
  warm-up requests. p95 was `2.45 ms`; the validator rejects a changed/untraceable p95 or a false
  claim that container latency was measured.
- UI Node harness covers loading, matched success, ambiguous/empty-candidate, and API error states.
  Static and dynamic checks confirm backend-supplied markup remains text and `innerHTML`,
  `insertAdjacentHTML`, and `eval` are not used.
- Secret scan found only the documented local-only Compose PostgreSQL password; no API keys,
  private keys, or hardcoded production credentials were found.
- `python3 -m pytest` was unavailable because pytest is not installed in the host interpreter;
  the same unittest-compatible suite was run directly and passed.
- The host interpreter still cannot build a standalone wheel offline because it lacks setuptools
  and the uv cache has no `setuptools>=75`; however, the no-cache Docker build downloaded its
  declared dependencies and successfully built and installed the project wheel.

## Findings

### Blocker

None for demonstrating the explicitly documented offline fixture path.

### Important

1. **The PostgreSQL vector path uses a deterministic lexical baseline, not a neural model.** T10
   verifies materialization, version/readiness checks, and exact pgvector execution with
   `hashing-v1`. Its positive alias/fixture results must not be described as sentence-transformer
   semantic quality, and database latency at the planned 3,000-row scale is not measured.
2. **External neural models are not integrated.** The verified dense provider is `hashing-v1` and
   reranker is `heuristic-v1`. `config/models.example.json` still contains replacement placeholders;
   selecting an external provider fails closed. Do not describe the reported results as a
   sentence-transformer or cross-encoder benchmark.
3. **Dependency constraints are selective, not a complete lock.** The compatibility-sensitive
   FastAPI/Starlette/TestClient/AnyIO/Pydantic/Uvicorn set is constrained and container-verified,
   with legacy `httpx` removed. PostgreSQL extras and unlisted transitive/build dependencies remain
   range-resolved and require a broader lock/reverification before a production database release.
4. **The external Wiki pilot is a review queue, not a catalog expansion claim.** Its 100 rows are
   source-attributed and reproducible, but all lack verified colors and canonical UUIDs. The
   source-derived text remains subject to CC BY-SA, and no formal legal or security sign-off was
   performed in this Lite milestone.
5. **T31 reduces review work but does not perform human verification.** Exact family-name matches
   are useful candidate links, while unmatched names are only possible new families. Neither case
   establishes a release variant, color, or canonical UUID without a reviewer decision.
6. **T32 is a queue, not a completed label set.** Its suggested actions are machine-generated and
   cannot be reported as human labels. The 53 pending entries require a named reviewer and evidence
   before a later promotion validator may accept them.
7. **T33 still requires the project owner's confirmation.** Exact family names justify a bounded
   merge recommendation, but differing years/series and unknown Wiki colors prevent variant-level
   mapping. Even Subaru's shared Zamac token remains supporting evidence rather than proof.
8. **T34 accepts family links only.** The recorded conversation authorization is traceable inside
   the repository but is not cryptographically signed. None of the four decisions may be described
   as canonical variant verification or used as evaluation labels.
9. **T35 is research, not a human label.** Nine source-backed creation recommendations and one hold
   are easier to review, but none may be counted as an accepted family until an attributable owner
   decision is validated. Source pages may change after the recorded research date.
10. **T36 accepts families only inside the review decision layer.** The nine accepted creations do
    not yet exist in `human_backed_catalog.json`, the canonical catalog, runtime retrieval, or
    PostgreSQL. Describing them as nine new searchable products would be incorrect.
11. **T37 remains a research artifact even after T38.** Its reviewer fields stay empty by design;
    attribution exists only in the separate T38 decision layer. The homonymous-name check protects
    family identity, but it does not identify which tool HYW60/HYX61 represent.
12. **T38 accepts family outcomes, not searchable identities.** The new decisions retain complete
    owner attribution and history, but the eighteen accepted new families across both batches are
    not yet objects in `human_backed_catalog.json`, the canonical catalog, or PostgreSQL.
13. **T39 is a recommendation packet, not a decision batch.** All ten researched names satisfy the
    current two-source rule, but none is accepted or searchable. Related-page evidence reduces name
    confusion; it does not prove release colors, variants, or physical identity on its own.
14. **T40 accepts family outcomes, not catalog objects.** The ten new approvals are attributable and
    cumulative, but they do not mint stable review IDs, canonical variants, PostgreSQL rows, or
    runtime candidates. All eighteen current release rows remain variant-held.
15. **T41 preserves tool ambiguity rather than hiding it behind toy numbers.** The Mazda and Nissan
    release codes identify particular pages, but the grouped family keys reuse names across distinct
    same-scale tools. Both recommendations remain held until the family identity becomes tool-
    qualified; none of the other eight recommendations is owner-approved within the T41 artifact.
16. **T42 accepts review outcomes, not searchable records.** Eight new-family outcomes are now
    owner-attributed and the two name collisions are completed holds, but no stable review ID,
    canonical variant, PostgreSQL row, or Dual-RAG candidate was created. All twenty-three current
    release rows remain variant-held.
17. **T43 closes research coverage, not owner adjudication.** The final nine pending families now
    have source-backed recommendations, but reviewer fields remain empty. Power Wheels is a renamed
    Bogzilla release, while Standard Kart and BNR32 expose multiple same-scale tools; converting any
    recommendation into a catalog entity before T44 would bypass the decision boundary.
18. **T44 closes family adjudication, not materialization.** All 53 family questions now have an
    attributable outcome, but the 42 accepted creations are still decision-layer concepts rather
    than stable human-catalog entities. All 100 release variants remain held, and neither Dual-RAG
    retrieval nor PostgreSQL contains these new family outcomes.
19. **T46 materializes review families, not runtime documents.** The registry and stable IDs now
    exist, but they are explicitly excluded from retrieval and PostgreSQL. Describing the 42 new
    families as Dual-RAG candidates or the 100 releases as variants would still be incorrect.
20. **T47 is a proposed integration contract, not shipped v2 retrieval.** The projection, typed
    document/API models, and v2 index do not exist until owner confirmation and implementation.
    Exact-name simulation is not independent evidence and cannot support a quality claim.

### Later

1. Add an actual browser smoke test if UI behavior beyond the Node DOM harness becomes release
   critical.
2. Add readiness-state coverage for a retriever/model that fails after startup, not only missing or
   unsupported dependencies at app creation.

## Recommended next task

The requested R7, R11, R13, Docker/Python 3.12 runtime, runtime reporting, selective dependency-
constraint, T04/T07/T09/T10 database milestones, T26–T29 human-data/Dual-RAG milestones, and the
T30–T44 external-data intake/pre-review/queue/evidence/research/decision milestones are QA-closed
for their stated Lite scope. T45–T46 specify, implement, and verify the stable family registry. T47
now provides the proposed family-level human-knowledge projection, typed retrieval, debug API/UI,
readiness, and canonical-isolation contract. After project-owner confirmation, T47.1 should build
the deterministic 42-document projection before runtime code changes. Casting-grouped holdout
evaluation and database materialization remain separate later gates before additional yearly lists
expand the corpus toward roughly 3,000 reviewable variants. Exact pgvector quality and latency must
be remeasured at that scale.
The next human-knowledge evaluation task remains an independently written, casting-grouped holdout
set; until that evidence exists, the human source stays debug-only. A complete dependency-lock
review, active post-startup database health polling, external neural models, and a justified T14
reranker remain deferred until held-out evidence supports them.
