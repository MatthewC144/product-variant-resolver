# T49 — Persistence design and release-variant roadmap

Date:2026-09-14. Lite. DRAFT; no owner design approval or implemented tables/adapters yet.

Historical status above refers to the planning checkpoint. Current scoped T49.2 owner「執行測試」
after its explicit isolated test proposal authorizes only the new disposable storage lane. Alembic0002
now implements hk_snapshot/hk_document; repository/verifier contract and actual SQL evidence are in
`docs/evidence/t49-2-human-knowledge-postgres.md`. Remaining table/profile/release proposals remain
DRAFT, not broadly approved. hk_embedding/release tables/default integration are not implemented.
The original plan/source exclusion metadata stays immutable in a separate authorized test namespace.

## Overview and current evidence

The canonical database already has `product_variant`, aliases, identifiers, provenance, FTS and
vector(192) tables. Those are canonical-only; do not reuse them for unreviewed Wiki/human data.
Human RAG currently reads142 file-backed typed documents. Its v4 identity admission is casting-only;
matching generic colors cannot admit unrelated families. Human hits do not influence final UUID,
status/confidence/product or canonical ranking/calibration/policy.

The Wiki pilot has100 source rows, all color null, no dedicated wheel/tampo fields; all remain
release-held. Human labels form97 castings/100 provisional groups, not100 newly verified releases.
Existing canonical `ProductView` and seven-field UUID policy have no wheel/tampo identity field;
`series_position` is parsed but not part of legacy identity either. Expand through new contracts,
not in-place policy edits or the assumption the same casting identifies one final product.

## Architecture and independent lanes

```text
Existing frozen human files ──► validated142-doc dry-run plan
                                   └─► authorized hk snapshot DB (debug evidence only)
Frozen/later-approved source rows ─► release observations + per-field evidence
                                   └─► owner review/held drafts (not canonical products)
Existing canonical catalog/DB ─────► unchanged final UUID/product/status/confidence
Future approved variant protocol ──► new versioned canonical promotion proposal, separately gated
```

T49 first establishes snapshot persistence and measured optional retrieval. The release lane is
a roadmap and bounded future review pilot, not bundled promotion. All code/doc/data remains within
the independent project directory; SQL volumes/secrets/local.env stay excluded from Git.

## Proposed storage model (not existing database objects)

| Table | Key/contents | Identity boundary |
|---|---|---|
| hk_snapshot | snapshot_id, schema_version, source hashes, doc counts, checksum, import event | Immutable complete snapshot; no automatic active switch |
| hk_document | (snapshot_id, knowledge_uuid), unique(snapshot_id, knowledge_id), knowledge_type, original payload/checksum | Exactly100provisional+42review-family; held/merge-source families excluded |
| hk_embedding | (snapshot_id, knowledge_uuid, embedding_version), vector192/checksum | Explicit experiment only; independent of canonical embeddings |
| release_source_record | source_record_id/revision/row, raw fields, attribution/access evidence | Observation identity only, not semantic release/canonical UUID |
| release_field_observation | record_id, field_name, raw/normalized value, source/evidence/status | Null unknown values; conflicting observations retained |
| release_review_event | immutable event_id, draft refs, field/value hashes, reviewer/time/reason/outcome | Append-only confirmed/held/rejected field decisions |

Typed document payloads preserve all142 current fields, not lossy common-name/color columns.
All child snapshot rows have foreign keys; importer validates exact expected IDs/types/payloads
before opening its transaction. Repeat equal snapshot => verified no-op; same ID/different bytes
=> collision error. No DROP/DELETE of unrelated tables/snapshots, no UUID upsert collision repair.
Migrations are additive after canonical0001; optional DB/profile names must not point at a user's
existing database by default. Snapshot selection requires explicit ID+hash, not latest timestamp.

## Interfaces and first bounded delivery

Proposed new module `human_knowledge_snapshot.py`: strict source-hash/count/exclusion validation,
typed142-row immutable plan and canonical sorted roundtrip serialization. Proposed script
`plan_human_knowledge_snapshot.py --check --output NEW_REPORT`: local files only, no SQL/network,
exclusive publication; success implies an import PLAN, not completed persistence.

Later new repository/migration modules accept an explicitly supplied isolated DB URL and snapshot
plan. Avoid adding `--write` to dry-run tooling. Separate verifier shows before/after counts,
rollback-on-invalid, idempotence, ID/payload parity and zero canonical table mutations.

Runtime integration needs a new versioned storage/retriever artifact because current v4/scorer/
config/service sources are evidence-bound. Do not change their hashes and reuse existing reports.
An opt-in adapter may materialize exact DB142documents into the unchanged mathematical posting
algorithm in a new profile. This is storage parity, not per-query SQL/pgvector retrieval. If dense
scoring moves into SQL, castings must still pass exact/character admission before vector scoring,
the full allowed union≤50 must be considered, and fusion/budgets stay equivalent. HNSW/global vector
TopK could drop eligible targets and is out of scope. Freeze/run a new development-only protocol
before choosing any database path. Old final105 queries are never reused for selection/live replay.

Keep FastAPI `/resolve`, `/health` and existing debug discriminator unchanged in the default profile.
Any additional public release-draft or wheel/tampo contract requires separate version/approval.
Missing/unavailable/mixed optional snapshot =>503; file default is not a fallback for broken opt-in.

## Release evidence and identity design

Each field stores value plus its exact observation/evidence/reviewer state, not a free-floating
confidence number. Proposed fields: casting/tool_lineage_ref, brand/scale, release_year, series,
collector/toy number, edition, color, wheel_type, tampo_description, packaging_variant. Keep an
explicit `unknown/pending/confirmed/conflicted` state and source observation separately; absent
field is null, not an empty-string equivalence or a positive match. Source IDs/toy numbers are
evidence links, not proof that attributes agree or globally unique release identifiers.

Example: same casting/red/2025 with wheelA vs wheelB remains two potential variants; same casting
with both wheel fields missing is two unresolved observations, not one confirmed release. A year
in a casting name and a release year must be reviewed separately. Rewording a tampo description
does not silently create a new canonical identity; grouping needs controlled reviewed descriptors.
A single official manufacturer release reference may support specific directly described fields;
otherwise seek corroborating non-duplicated publisher evidence and show disagreement. AI notes
and Wiki list placement are never sufficient release approval. All owner decisions bind exact
values and evidence; unresolved tool lineages from seven holds remain held.

Propose identity-v2 only after actual reviewed collision/discriminator evidence. Do not simply add
wheels/tampo to legacy `IDENTITY_FIELDS`, which would remint existing products. New future variant
IDs require reviewed identity mappings/contract and separate rollout approval. This stage creates
only deterministic observation/draft IDs; no canonical minting or promotion.

## Source method, access and scale milestones

Start with offline frozen100rows and their nulls; build a small review queue before more collection.
For later authorized text collection, prefer existing revision/wikitext API adapter over brittle
HTML/photo parsing. Inspect casting-page release tables only after their access/rights and parser
formats are confirmed; year lists alone currently lack verified color/wheel/tampo detail.

Read-only web checks on2026-09-14 failed to fetch Fandom licensing and Hot_Wheels pages with402
through the browsing service. This is not evidence that the source server forbids all API access
or permits collection. Current rights/API/robots availability remains unverified; no bypass used.
The old pilot's reportedCC-BY-SA/attribution is frozen historical metadata, not a current clearance.
Before any collection, check current source-specific access/terms and freeze source manifest and
serial request budget; stop on denial/rate limits. MediaWiki's official API guidance recommends
descriptive User-Agent, serial/batched reads and caching; it is general guidance, not Fandom
permission. See [API etiquette](https://www.mediawiki.org/wiki/API:Etiquette).

Proposed milestones:100offline source rows →500unique real staged rows →1,500→about3,000.
Each batch requires approved pages/revisions/license record, checksum, parser tests, duplicate/
conflict report and owner handoff. Preserve revision observations but count release dedup separately;
extra toy numbers, duplicate editions or repeated snapshots do not inflate confirmed-variant count.
Stop rather than pad synthetically or reduce review requirements to hit a quota. Report castings,
source observations, dedup releases, held/reviewed variants, human docs and canonical rows separately.

## Testing strategy and later variant evaluation

Storage: strict142-row IDs/types/payloads, source tampering, held/merge exclusions, row ordering,
bad-input-before-write, transaction rollback, repeat no-op, snapshot collision, no canonical mutation,
file/DB roundtrip parity and optional readiness503. Runtime/cost experiments freeze exact workloads,
samples/query IDs, host/SQL/network/startup scope and profile hashes BEFORE outputs. Use already-viewed
199development cases as disclosed diagnostic parity only; preserve existing final outputs.

Variant: future approved labeled dataset must include same casting/different colors/year/series,
wheel/tampo differences, insufficient-title attributes, multiple colors/conflicting year, unknown
attributes and unrelated listings. Split duplicate listing/source sessions and release identities
without leakage; ensure dataset has distinguishable same-casting groups in each evaluation split.
Freeze exact labels/gates before output; measure exact-variant Top1/Recall@K, false-match precision,
abstention/ambiguous coverage, per-attribute/group errors and cost separately from family recall.
Treat canonical promotion and matching rollout as a new feature, not an assumed T49 output.

## Error handling, security and alternatives

Fail before writes on malformed/stale/partial plans; preserve old snapshots/records. Optional DB
dependency failures =>503, not fabricated empty successful evidence. New crawling must stop on
access/rights uncertainty; no images or auth bypass. Use parameterized SQL, explicit test DB URLs,
restricted roles, secret-free reports and Git-excluded volume/env configuration. Canonical and
human/staging tables are separate even if later housed in one database.

Continue files-only is valid until optional persistence is approved; PostgreSQL adds durable
transactions/typed relations and matches the existing stack, but introduces startup/migration/
resource costs. JSONB preserves versioned human payloads while release observations get typed
field/evidence rows; a single unstructured blob would obscure conflicts and approval. ANN/neural
search is deferred: persistence does not justify changing proven eligibility/fusion. At10×, storage
rows and vectors are affordable only as a hypothesis; actual network/posting/SQL cost needs a frozen
benchmark. Most likely failure is promoting incomplete release evidence because the family passed.
