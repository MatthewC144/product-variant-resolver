# Product Variant Resolver

A Lite/MVP, offline-first resolver that maps noisy Hot Wheels marketplace titles to a canonical
fixture product—or abstains with `ambiguous` / `no_match`. The verified default is deliberately
dependency-light: catalog-derived signals, token sparse retrieval, deterministic `hashing-v1`
dense retrieval, structured soft conflicts, RRF, logistic confidence, and abstention behind
FastAPI.

This is a portfolio-quality fixture validation, not evidence of production accuracy or marketplace
coverage.

## Human-labeled auxiliary data

The repository also includes `data/human_labeled_names.json`, a frozen auxiliary corpus derived
from real noisy scans reviewed by a human. It contains 101 confirmed labels: 91 records pair an
initial recognition name with the human-verified name, while 10 retain an explicit `no_candidate`
initial failure and the human answer. The source and generated-file checksums are recorded in
`data/human_labeled_names_manifest.json`.

This corpus is currently intended for candidate-name evaluation, name normalization, and future
catalog alignment. It is deliberately excluded from the headline canonical-resolution metrics,
calibration training, and threshold selection because its names have not yet been mapped to this
repository's immutable catalog UUIDs and slugs.

The current conservative alignment is frozen in
`data/human_labeled_catalog_alignment.json`. Exact normalized brand/casting matching finds two
`Toyota Supra` records at casting-family level, but neither contains enough compatible variant
evidence to select one of the 12 synthetic Toyota Supra variants. The result is therefore 0
canonical mappings, 2 family-only matches, and 99 unmapped records. This low coverage is expected:
the fixture catalog has only 10 synthetic casting families, while the reviewed corpus contains 97
real casting names.

`data/human_backed_catalog.json` now turns those reviewed labels into a separate catalog draft:
97 stable casting entities and 100 provisional variant groups derived from all 101 records. One
exact duplicate structured label is merged while retaining both source cases and both human names.
The draft is eligible for sparse/dense candidate retrieval and human review, but every variant is
marked `needs_canonical_review`; it is not yet used for canonical API responses or calibration.

## Architecture

```text
Debug UI / API client
        |
 FastAPI: /resolve, /health
        |
 generic signal extraction
        |
        +------------------------------+
        |                              |
 canonical catalog RAG          human knowledge RAG v2
 sparse + dense + structured    sparse + hashing dense
        |                              |
 RRF + calibration/policy       variant + family review evidence
        +------------------------------+
        |
 matched | ambiguous | no_match + debug evidence
```

Product knowledge—aliases, colors, series, identifiers, and variant attributes—lives in the
catalog. Conflicting structured signals remain soft ranking evidence instead of removing a
candidate. RRF stays on the default runtime path because the local heuristic reranker added `0.0`
absolute Top-1 accuracy on the frozen test; enable it only for an explicit experiment with
`PVR_RERANKER_ENABLED=true`. No external cross-encoder was evaluated.

The runtime now uses two retrieval corpora. The canonical fixture catalog is the only source allowed
to produce a final UUID. Human Knowledge RAG v2 independently ranks 100 human-backed provisional
variants and 42 accepted review families. The debug API and UI identify each result as either a
`provisional_variant` or `review_family` and expose only fields appropriate to that type. A human-
only hit can help explain a `no_match`, but cannot silently become a canonical product.

## Start the offline path

The source checkout remains convenient for development. Host QA used Python 3.14.6; the separately
verified Docker runtime uses the project-targeted Python 3.12.14.

```bash
python -m pip install -e '.[dev]'
PYTHONPATH=src uvicorn product_variant_resolver.api:app --reload
```

Open `http://127.0.0.1:8000/` for the same-origin debug UI, or call the API:

```bash
curl --fail --json '{"title":"2022 Chevy Nomad Red #101","debug":true}' \
  http://127.0.0.1:8000/resolve
curl --fail http://127.0.0.1:8000/health
```

The normal response omits candidates, internal ranks/scores, and timings. `debug=true` exposes a
bounded explanation payload. UI values are rendered as text, and resolution logs omit raw titles.

## Verify and reproduce the fixture report

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/validate_fixture_data.py
python scripts/import_human_labeled_names.py --source /path/to/labeling-queue.csv
python scripts/align_human_labeled_names.py
python scripts/build_human_backed_catalog.py
PYTHONPATH=src python -m product_variant_resolver.evaluation
PYTHONPATH=src python scripts/train_calibration.py --output-directory artifacts
PYTHONPATH=src python scripts/generate_evaluation_report.py \
  --output-directory reports/fixture-v1
```

Generated calibration and policy files can be selected with `PVR_CALIBRATION_ARTIFACT` and
`PVR_POLICY_ARTIFACT`. Without them, the API uses the explicit fixture fallback versions.

## Demonstrated result

The checked-in report covers exactly **21 synthetic fixture test cases** (12 matched) drawn from a
120-product synthetic/curated catalog and a 100-case grouped benchmark.

| Metric | Evidence result |
|---|---:|
| Recall@25 | `1.0` |
| Top-1 accuracy | `1.0` |
| Hard-negative accuracy | `1.0` (4/4) |
| Precision | `1.0` |
| False-match rate | `0.0` |
| Coverage | `0.8333` |
| Heuristic reranker gain over RRF | `0.0` |
| Warmed in-process ASGI p95 | `7.9523 ms` |
| Host→Docker loopback p95 | `4.721208 ms` |

The in-process value uses 21 sequential FastAPI/TestClient samples after five excluded warm-ups at
K=25. A separate QA regeneration reported `2.45 ms`, illustrating expected smoke-run variance at
this scale. The host→Docker value is the separately scoped loopback artifact described below. See the
[versioned report](reports/fixture-v1/evaluation-fixture-v1-test.md),
[QA review](specs/product-variant-resolver/review.md), and
[MVP evidence](docs/evidence/product-variant-resolver-mvp.md).

## Review-only Hot Wheels Wiki pilot

The repository includes a 100-row text-only staging pilot from the 2025 Hot Wheels Wiki mainline
list. It was fetched with an identified client through the MediaWiki API and frozen at revision
`790665`. All records remain `needs_canonical_review`, have null canonical UUIDs, and are excluded
from resolver accuracy, calibration, and threshold training. The API and Docker runtime do not load
this directory.

Validate the checked-in snapshot or rebuild normalized data without another network request:

```bash
PYTHONPATH=src python3 scripts/validate_fandom_catalog_pilot.py
PYTHONPATH=src python3 scripts/fetch_fandom_catalog_pilot.py \
  --raw-input data/external/hot-wheels-wiki/pilot-2025/raw.json
```

The normalized data omits the photo column and does not infer color from filenames. Source,
revision, transformation notes, contributor attribution, and CC-BY-SA terms are documented in the
[external-data README](data/external/hot-wheels-wiki/README.md). A live refresh uses two API
requests—site rights plus one page revision—and should be performed only after rechecking the
source access and license conditions.

The deterministic cross-catalog review compares every staged row with both the canonical fixture
and the human-backed draft using exact normalized brand and casting names only. The current report
covers 100 rows / 53 distinct casting families: 9 rows across 4 families have an exact
human-catalog candidate, while 91 rows across 49 families have no exact candidate. None are
automatically promoted.

```bash
python3 scripts/review_fandom_catalog_pilot.py --check
```

The full row-level decisions and frozen input/output checksums are in
[`review.json`](data/external/hot-wheels-wiki/pilot-2025/review.json) and
[`review-manifest.json`](data/external/hot-wheels-wiki/pilot-2025/review-manifest.json).

For actual human adjudication, the 100 rows are grouped into a 53-family queue. The readable
[`adjudication worksheet`](data/external/hot-wheels-wiki/pilot-2025/adjudication-queue.md) puts the
four exact existing-family candidates first and the 49 research-required families second. All
decisions are initially pending, and the queue cannot be used as a promotion file.

```bash
python3 scripts/build_fandom_adjudication_queue.py --check
```

The four priority-1 families also have a compact
[`side-by-side evidence report`](data/external/hot-wheels-wiki/pilot-2025/priority-1-evidence.md).
It shows every Wiki release row beside the original and human-verified names already stored in the
human-backed catalog. The machine recommendation is family-level merge for all four and variant-
level hold for all four; reviewer confirmation remains empty.

```bash
python3 scripts/build_fandom_priority_one_evidence.py --check
```

The project owner's follow-up authorization is recorded separately in
[`priority-1-decisions.json`](data/external/hot-wheels-wiki/pilot-2025/priority-1-decisions.json).
The validated result accepts four casting-family links, keeps all nine release variants held, and
leaves 49 family decisions pending. It still creates no canonical identity or PostgreSQL row.

```bash
python3 scripts/apply_fandom_adjudication_decisions.py --check
```

Priority-2 research now has a first bounded batch instead of treating all 49 unmatched names as
automatically new. The readable
[`batch-01 research report`](data/external/hot-wheels-wiki/pilot-2025/priority-2-batch-01-research.md)
checks the first ten pending families against a dedicated Wiki casting page and at least one
non-Fandom publisher. Nine meet the evidence rule for a machine `create_new_casting`
recommendation. `'55 Chevy` remains on hold because that title covers three distinct casting tools.
These are not reviewer decisions: all 19 represented releases remain variant-held and no record is
written to the canonical catalog or PostgreSQL.

```bash
python3 scripts/build_fandom_priority_two_research.py --check
```

The project owner's follow-up approval is stored separately in
[`priority-2-batch-01-decisions.json`](data/external/hot-wheels-wiki/pilot-2025/priority-2-batch-01-decisions.json).
The validator accepts all nine proposed new-family decisions, keeps `'55 Chevy` held, preserves the
four earlier family merges, and derives a cumulative 14-completed / 39-pending queue. The 28 release
rows represented by completed family decisions still remain variant-held; “accepted new family” is
a review-layer decision, not a canonical UUID or database row.

```bash
python3 scripts/apply_fandom_priority_two_decisions.py --check
```

Priority-2 batch 02 continues from that cumulative 14-completed / 39-pending queue rather than
restarting from the original list. Its
[`batch-02 research report`](data/external/hot-wheels-wiki/pilot-2025/priority-2-batch-02-research.md)
covers the next ten families and eighteen Wiki releases. Nine receive machine
`create_new_casting` recommendations. `Batman and Robin Batmobile` remains held because the exact
display name is also used by a separate 2004 100% Hot Wheels casting tool, so the staged name is
not sufficient to choose one lineage. Reviewer confirmation is still pending for all ten; every
release remains variant-held and none enters the canonical catalog, PostgreSQL, or runtime.

```bash
python3 scripts/build_fandom_priority_two_research.py --batch 2 --check
```

The owner's follow-up approval is recorded in
[`priority-2-batch-02-decisions.json`](data/external/hot-wheels-wiki/pilot-2025/priority-2-batch-02-decisions.json).
The validated batch-02 cumulative queue preserves all earlier decision history and now reports 24
completed / 29 pending families: 4 existing-family merges, 18 accepted new-family decisions, and 2
holds. All 46 represented release rows remain variant-held, and accepted families still have no
canonical UUID, PostgreSQL row, or runtime identity.

```bash
python3 scripts/apply_fandom_priority_two_decisions.py --batch 2 --check
```

Priority-2 batch 03 continues from the 24-completed / 29-pending cumulative queue. Its
[`batch-03 research report`](data/external/hot-wheels-wiki/pilot-2025/priority-2-batch-03-research.md)
covers the next ten families and eighteen Wiki releases. All ten exact names have a dedicated Wiki
casting page plus independent corroboration and therefore receive machine `create_new_casting`
recommendations. The evidence explicitly keeps Fiat 500e separate from Fiat 500 and the newer
Hirohata Merc separate from the earlier, differently named `'51 Merc` tool. These are not owner
decisions: reviewer confirmation remains pending, all eighteen variants remain held, and nothing
enters the canonical catalog, PostgreSQL, or runtime.

```bash
python3 scripts/build_fandom_priority_two_research.py --batch 3 --check
```

The owner's follow-up authorization for all ten batch-03 family recommendations is stored in
[`priority-2-batch-03-decisions.json`](data/external/hot-wheels-wiki/pilot-2025/priority-2-batch-03-decisions.json).
The validated cumulative queue preserves all prior history and now reports 34 completed / 19
pending families: 4 existing-family merges, 28 accepted new-family decisions, and 2 holds. All 64
release rows represented by completed family decisions remain variant-held. The acceptance still
does not create stable catalog IDs, canonical variants, PostgreSQL rows, or runtime identities.

```bash
python3 scripts/apply_fandom_priority_two_decisions.py --batch 3 --check
```

Priority-2 batch 04 continues from the 34-completed / 19-pending cumulative queue. Its
[`batch-04 research report`](data/external/hot-wheels-wiki/pilot-2025/priority-2-batch-04-research.md)
covers the next ten families and twenty-three Wiki release rows. Eight names meet the two-source
creation rule. `Mazda MX-5 Miata` remains held because distinct 1991 and 2025 1:64 tools use that
display name; `Nissan Skyline 2000GT-R LBWK` remains held because the regular and Tooned tools share
the name, with this batch's HYW79/HYY30/HYX54 rows belonging to the Tooned page. Reviewer
confirmation is pending, every variant remains held, and no catalog, PostgreSQL, or runtime record
is created.

```bash
python3 scripts/build_fandom_priority_two_research.py --batch 4 --check
```

The owner's follow-up authorization for the exact batch-04 split is stored in
[`priority-2-batch-04-decisions.json`](data/external/hot-wheels-wiki/pilot-2025/priority-2-batch-04-decisions.json).
The cumulative queue now reports 44 completed / 9 pending families: 4 existing-family merges, 36
accepted new-family decisions, and 4 holds. The Mazda and Nissan name collisions remain held, and
all 87 release rows represented by completed decisions remain variant-held. This decision layer
does not create catalog UUIDs, PostgreSQL rows, or runtime identities.

```bash
python3 scripts/apply_fandom_priority_two_decisions.py --batch 4 --check
```

Priority-2 batch 05 is the final research slice for the current 100-row pilot. Its
[`batch-05 research report`](data/external/hot-wheels-wiki/pilot-2025/priority-2-batch-05-research.md)
covers all nine remaining pending families and thirteen release rows. Six receive machine
`create_new_casting` recommendations. Nissan Skyline GT-R (BNR32) and Standard Kart remain held
because their display names span distinct same-scale tools; Power Wheels Dune Racer remains held
because HYX52 is a renamed Bogzilla release rather than evidence for a new casting. Reviewer
confirmation remains pending, every variant stays held, and no catalog, PostgreSQL, or runtime
record is created.

```bash
python3 scripts/build_fandom_priority_two_research.py --batch 5 --check
```

The owner's authorization for the exact final six-create/three-hold split is stored in
[`priority-2-batch-05-decisions.json`](data/external/hot-wheels-wiki/pilot-2025/priority-2-batch-05-decisions.json).
The final cumulative queue is now fully adjudicated at family scope: all 53 families have an
attributable outcome, comprising 4 existing-family merges, 42 accepted new-family decisions, and
7 holds. All 100 Wiki release rows remain variant-held and promotion eligibility remains zero.
“Fully adjudicated” therefore means that the review question has been answered; it does not mean
that stable catalog UUIDs, canonical variants, PostgreSQL rows, or runtime identities were created.

```bash
python3 scripts/apply_fandom_priority_two_decisions.py --batch 5 --check
```

The completed
[`review-family-materialization`](specs/review-family-materialization/requirements.md) milestone
keeps family decisions separate from release variants. Its deterministic
[`review-family registry`](data/review_family_registry.json) contains 42 stable family-only review
entities, 4 links to existing human-backed families, and 7 explicit non-indexable exclusions. All
100 source rows remain held release references; provisional variants, canonical promotions,
runtime-indexed families, and PostgreSQL rows all remain zero.

```bash
python3 scripts/build_review_family_registry.py --check
```

The family-level runtime contract is documented in
[`family-level-human-knowledge`](specs/family-level-human-knowledge/requirements.md). It derives a
separate 42-document runtime projection instead of loading the T46 audit registry directly, then
combines those family documents with the existing 100 provisional-variant documents in the second
RAG source. The contract keeps all human knowledge debug-only and leaves canonical ranking,
confidence, PostgreSQL, and calibration unchanged.

T47.1 now materializes the allowlisted projection in
[`review_family_knowledge.json`](data/review_family_knowledge.json). It contains only accepted
family identity, name/alias, and source-record references; merge links, holds, release details,
decision reasons, and evidence URLs are not copied into documents. Its manifest freezes the two
T46 inputs, output checksum, 42/4/7 accounting, searchable-field policy, and zero
variant/canonical/PostgreSQL counts.

```bash
python3 scripts/build_review_family_knowledge.py --check
```

T47.2 now loads that projection through strict typed models and combines it with the 100 existing
provisional variants in `human-knowledge-hybrid-v2`. The second RAG therefore searches 142 documents
in one sparse/hashing-dense/RRF ranking pool. Missing, malformed, checksum-stale, field-widened, or
identity-invalid family data makes readiness fail with HTTP 503. Health exposes the family
projection version and traces report bounded variant/family candidate counts without raw titles.
The combined human candidates still cannot enter canonical ranking or confidence.

T47.3 exposes the mixed ranking as a strict discriminated debug contract. Variant items keep their
casting/provisional-variant IDs and reviewed labels; family items expose review-family IDs, aliases,
and source-record provenance without null or fabricated variant fields. The debug payload includes
the frozen family projection version, and one request limit bounds the combined list. The local UI
labels both types and renders all external names as inert text. An exact Proton Saga query therefore
shows useful family review evidence while the canonical answer remains `no_match`.

T47.4 closes the Lite integration review. The dedicated
[`family-level QA review`](specs/family-level-human-knowledge/review.md) maps FHK-R1–FHK-R16 to
passing evidence, and the
[`Human Knowledge RAG v2 evaluation`](docs/evidence/ai-evals/dual-rag-human-knowledge-v2.md)
separates debug-wiring safety from unmeasured retrieval accuracy. The complete 184-test suite,
deterministic source chain, and frozen canonical evaluation pass without changing canonical or
PostgreSQL data. Independent casting-grouped family evaluation remains the next gate.

The confirmed T48 contract is documented in
[`family-retrieval-evaluation`](specs/family-retrieval-evaluation/requirements.md). It does not reuse
the exact-name smoke matrix or repurpose staging-only Fandom rows as test truth. Instead it freezes a
separately written, owner-approved 105-case test pack before scoring: two challenge styles for every
accepted family plus merge, hold, and unrelated controls. Metrics and PASS thresholds are
precommitted, and a failure must remain visible rather than tuning on the same holdout. T48.1 now
implements the fail-closed builder, source/code checksum freeze, separate query-pack freeze/check,
owner-decision validation, deterministic benchmark build/check, and negative tests. The formal 105
queries are now independently authored and checksum-frozen in T48.2: 42 marketplace-noise pairs,
42 lexical-variation pairs, 4 merge controls, 7 held-identity controls, and 10 zero-overlap controls.
The owner confirmed that unchanged pack, and T48.3 froze all 105 attributable labels plus the
unscored benchmark. T48.4 then ran the existing retriever once and published the complete
[`JSON/Markdown evaluation`](reports/family-retrieval-v1/evaluation.md) plus the
[`AI-eval record`](docs/evidence/ai-evals/family-retrieval-holdout-v1.md). The precommitted result is
**FAIL**: eight of nine gates pass, but lexical-variation Recall@5 is `31/42 = 0.7381`, below the
required `0.75`. Overall Recall@5 is `73/84 = 0.8690`; all marketplace-noise, merge, forbidden-
family, and unrelated controls pass.

T48.5 closes the [`Lite QA review`](specs/family-retrieval-evaluation/review.md) with 201/201 tests,
the complete deterministic data chain, unchanged canonical fixture metrics, T47 regression,
compilation, Compose, and scope checks passing. This is an engineering-verification PASS but a
retrieval-quality FAIL. The family source remains debug-only, same-set tuning is prohibited, and
T49 PostgreSQL/pgvector persistence plus the approximately 3,000-row expansion are blocked until a
redesigned retriever passes a newly authored v2 holdout.

The active next feature is the
[`Human Knowledge retriever redesign`](specs/human-knowledge-retriever-redesign/requirements.md).
It keeps the Dual RAG authority boundary unchanged and adds a deterministic character n-gram TF-IDF
candidate channel to the second RAG. HRR-T1 has now frozen the
[`199-case development-only pack`](docs/evidence/family-retrieval-development-v1.md): 42 families
times four deterministic transformations, 4 merge controls, 7 hold controls, and 20 unrelated
controls. Its 21-config grid and input/output hashes were committed before any retriever output;
the data is explicitly identity-derived and cannot support final accuracy. No selected runtime
configuration, v3 model artifact, or new final evaluation has been created.

HRR-T2 now implements the experimental v3 mechanics without activating them by default. The second
RAG can build a Unicode character bigram/trigram TF-IDF posting index from strictly allowlisted
identity names, union its candidates with token evidence, dense-rank only that bounded union, and
fuse available token/dense/character ranks. Typed API/UI debug fields expose character evidence and
index/artifact versions, while invalid artifact opt-in fails readiness. The implementation evidence
is recorded in
[`human-knowledge-retriever-v3-implementation.md`](docs/evidence/human-knowledge-retriever-v3-implementation.md).
HRR-T3 has now completed all 21 configurations on the frozen 199-case development pack, recording
4,179 case/configuration outputs and local 142-document / synthetic 3,000-document cost. The
[`development selection report`](reports/family-retrieval-development-v1/selection.md) is **FAIL**:
every configuration returns candidates for all 10 generic-no-identity negatives, has real-corpus
p95 `29.37–36.60 ms` (budget 25), and synthetic-scale p95 `337.15–377.28 ms` (budget 150).
Positive Recall@5 is `164–168/168`, merge retrieval `4/4`, and forbidden-family hits zero, but
these strengths do not override the failed safety/cost gates. V2 stays active, no v3 artifact or
new final holdout was created, and T49/real-catalog expansion remain blocked. The engineering
checkpoint passes 236 tests; the development-quality verdict remains FAIL. See the
[`AI-eval record`](docs/evidence/ai-evals/human-knowledge-retrieval-development-v1.md).

The active Lite follow-up is
[`Identity-Bounded Human Knowledge Retrieval`](specs/human-knowledge-identity-bounded-retrieval/requirements.md).
Its [design](specs/human-knowledge-identity-bounded-retrieval/design.md) replaces broad any-token
admission with casting-core evidence and redundant character pair comparisons with direct weighted
form-posting accumulation, under an isolated experimental v4 path. It retains the same 21-config
grid, all quality/safety/cost gates and owner-approved unseen final-test lifecycle. The new scale
workload also requires known synthetic identities to be retrieved, preventing a cheap empty-output
timing claim. **IBR-T1 complete:** the owner confirmed the three specifications, and the
[execution protocol](data/evaluation/human-knowledge-identity-development-v1/protocol.json) is frozen
with code/corpus/development/spec hashes, work limits and all 120 scale-query targets. The
[core audit](docs/evidence/human-knowledge-identity-protocol-v1.md) retains 142 documents/284 forms,
two same-casting variant collision groups and no cross-casting collision. The synthetic casting
cores are numeric-only, so their typo probes are not true core-name typo evidence.

**IBR-T2 complete:** isolated v4 now implements complete-core token admission, exact normalized
form-posting character scores, bounded dense/RRF ranking and query-local work/debug/UI metadata.
Independent mathematical checks and API/canonical/failure regressions pass. A separate opt-in
`PVR_HUMAN_KNOWLEDGE_IDENTITY_ARTIFACT` requires a checksum-valid, fully recomputable qualified
development report; missing/stale/failed evidence returns readiness 503, not silent v2 fallback.
V3/v4 artifact settings cannot coexist. The selected v4 artifact described below is experimental;
leave the setting unset for the unchanged default v2 path.
See [T2 evidence](docs/evidence/human-knowledge-identity-implementation-v1.md).

Current project checklist (engineering completion is not retrieval-quality approval):

- [x] Canonical resolver MVP: FastAPI, debug UI, sparse/dense/structured fusion, calibration/policy.
- [x] PostgreSQL catalog/migration/ingestion and canonical retrieval plumbing with prior QA evidence.
- [x] Human-data import/alignment: 101 source rows, 100 provisional variants, 97 real castings.
- [x] Fandom pilot/review governance and 42 family-only knowledge docs; combined human corpus 142 docs.
- [x] Independent v1 evaluation and v3 development comparison published, including their FAILs.
- [x] IBR-T1: owner-approved v4 protocol/core audit and 120-query synthetic workload frozen.
- [x] IBR-T2: v4 implementation, oracle/caps/isolated API/UI/evidence validation.
- [x] IBR-T3: all 21 configurations/4,179 real outputs and 2,520 scale outputs frozen; development PASS.
- [x] IBR-T4 preparation: freeze 105 new output-blind final question/reference pairs after winner commit.
- [x] IBR-T4 approval/labels: owner confirmed targets/scope; 105 decisions and benchmark frozen separately.
- [x] IBR-T5: one final score PASS, full Lite closure and fresh non-root/read-only Docker HTTP verification.
- [x] T49 planning: persistence/variant-roadmap drafted; broader owner G1 confirmation pending.
- [x] T49.1: narrowly authorized local-only142-document import-plan/checker;37focused tests PASS, no DB/network write.
- [ ] Later: isolated persistence and source/field-reviewed real variant expansion; separate rollout gates.
- [ ] End-to-end demonstration and beginner code review after project delivery.

**IBR-T3 complete:** all 21 settings pass the frozen development gates. The deterministic winner is
floor `0.50`, character weight `1.0`: positive Recall@5 `168/168`, Recall@1 `165/168`, MRR@5
`0.9911`, each style `42/42`, merge `4/4`, forbidden hits `0`, unrelated nonempty `0/20`.
Winner real/scale p95 is `2.07/45.14 ms` against `25/150 ms` budgets. Exact/edit/context synthetic
target hits are `60/60`, `20/20`, `20/20`. Raw latency, subgroup/work/source evidence is retained in
[selection JSON](reports/human-knowledge-identity-development-v1/selection.json),
[readable report](reports/human-knowledge-identity-development-v1/selection.md) and
[T3 evidence](docs/evidence/human-knowledge-identity-development-v1.md).

The [selected artifact](config/human-knowledge-retrieval-v4.json) passes genuine runtime/API loading.
For explicit experimental debug evaluation only:

```bash
PVR_HUMAN_KNOWLEDGE_IDENTITY_ARTIFACT=config/human-knowledge-retrieval-v4.json \
  uvicorn product_variant_resolver.api:app --host 127.0.0.1 --port 8000
```

At the T3 checkpoint, no final score or default switch had occurred. Development is already-viewed identity-derived
data, not independent final accuracy. Microbenchmarks are non-isolated Python 3.12.13/arm64/10-CPU
in-process retrieval only; not Docker/HTTP/SQL/load/production latency. First-setting startup/early
measurement briefly overlapped the pre-run test process, disclosed in evidence without rerunning.
The original FAILs remain published; see the T5 checkpoint below for design-only T49 eligibility. Synthetic 3,000-document workload is not 3,000 real
products inserted into PostgreSQL.

**IBR-T4 complete — owner-approved family benchmark frozen before the T5 score below.**
[Review all 105 frozen questions and intended targets](data/evaluation/family-retrieval-v2/owner-review.md).
The query pack has 84 positives (42 families × marketplace/lexical), 4 merge, 7 hold and 10 unrelated
controls. It rejects copied old final/development/indexed strings, compact duplicates and nonempty
old query-core reuse. Zero normalized/compact duplicates and unrelated token overlap. Same familiar
families, independently composed synthetic questions—not a blind author, live marketplace sample or
unseen-casting split. No new final candidate has been executed or viewed.

Authoritative query-pack SHA-256:
`b23b69912c678c027461c96eb23f113484c5a8ed6218c06d90026704abe5102b`.
Full case hashes/source checks are in its manifest; the owner table presents every query/target pair.
Owner target confirmation and consent following the variant-scope explanation are recorded in
[`approved/owner-decisions.json`](data/evaluation/family-retrieval-v2/approved/owner-decisions.json).
All 105 formal family labels are in
[`approved/benchmark.json`](data/evaluation/family-retrieval-v2/approved/benchmark.json), bound to
question/case/builder hashes. This is casting/family truth, not color/wheel/tampo/release-variant or
canonical ground truth. Held controls prohibit the held family; they do not require all valid hits
to disappear. That label-stage freeze did not run retrieval; T5 results are below. Coverage means retrieved **families/42**, not
positive-query response count. A misnamed
unapproved metadata draft is preserved under `family-retrieval-v2-superseded-draft-01`, not eligible
for approval or scoring. Questions were unchanged and no model output informed this correction.

```bash
PYTHONPATH=src .venv/bin/python scripts/author_family_retrieval_query_pack_v2.py --check
PYTHONPATH=src .venv/bin/python scripts/build_family_retrieval_benchmark_v2.py --check
PYTHONPATH=src .venv/bin/python scripts/build_family_retrieval_benchmark_v2.py --check-committed
```

The original question checker still describes its historical pending-review checkpoint; its flags
and source bytes remain immutable. Use the new benchmark checker for current approval status;
`--check-committed` refuses uncommitted or modified labels/builders before T5. Defaultv2 remains active.

**IBR-T5 final family-quality / Lite closure PASS.** Benchmark87bbd19 and evaluatorb86578c were
committed before exactly105 final query calls, zero final warmups/retries. All raw ranks/work/errors
were saved before label scoring; no final-set tuning or source-bound retriever/label changes.

| Final gate | Result |
|---|---:|
| Positive Recall@5 | 80/84 =95.24% |
| Positive Recall@1 | 77/84 =91.67% |
| MRR@5 | 0.93254 |
| Marketplace / lexical Recall@5 | 42/42 /38/42 |
| Family coverage / merge Recall@5 | 42/42 /4/4 |
| Forbidden families / unrelated nonempty / retrieval errors | 0 /0 /0 |

All9 inherited gates pass; four lexical misses remain in
[`evaluation.md`](reports/family-retrieval-v2/evaluation.md), with all105 rows in
[`raw-results.json`](reports/family-retrieval-v2/raw-results.json). This is approved synthetic
same-family retrieval, not independent population/unseen-casting, release/color/wheel/tampo accuracy.
Diagnostic finalp95=6.945209ms excludes extraction and includes serialization; no HTTP/production claim.

411 full tests pass. Fresh Docker Python3.12.14/non-root/read-only loopback HTTP validates defaultv2,
experimentalv4, identical non-debug canonical answers, debug/UI and missing/malformed/stale503.
The real packagingROOT failure was fixed with `PYTHONPATH=/app/src`, keeping pinned loader/model
bytes unchanged. A verifier fixture wrongly treated relocation of identical bytes as stale; corrected
to invalid mandatory evidenceSHA. Both failures remain published beside the successful runtime report.

```bash
PYTHONPATH=src .venv/bin/python -m product_variant_resolver.family_retrieval_final_v2_evaluation --check
```

Checking uses stored ranks, never final retrieval. `--run` refuses the existing reserved run directory.
See [final/closure evidence](docs/evidence/family-retrieval-final-v2.md). Next T49 DESIGN ONLY:
plan reviewed real catalog/variant attributes and targeted same-casting variant tests; no SQL writes,
3,000-row ingestion, defaultv4 deployment or production accuracy approval is implied.

**T49.1 local snapshot PLAN delivered; later database/variant implementation still gated.** Read the
[plain-language roadmap](docs/REAL-CATALOG-ROADMAP.md). New
[requirements](specs/human-knowledge-persistence-and-variant-roadmap/requirements.md),
[design](specs/human-knowledge-persistence-and-variant-roadmap/design.md), and
[tasks](specs/human-knowledge-persistence-and-variant-roadmap/tasks.md) separate142human-doc snapshot
persistence from100heldrelease field review. Actual pilot100colors remain null; wheel/tampo fields
are absent. About3,000unique real source rows is a staged-data goal, not3,000verified canonical
products. Owner execution after the detailed draft explanation is scoped only to T49.1, not full
sequential G1 approval or database writes. [Local plan/report](reports/human-knowledge-snapshot-v1/report.md)
preserves142typed documents, original UUIDs/provenance/exclusions and12pinned source fingerprints;
37new/448full tests PASS. No dataset rows, canonical UUIDs, migrations or default changes.
See [execution scope/QA](docs/evidence/t49-1-execution-scope.md). Current source access/rights remain
unverified; no bypass or media collection. Next needs explicit isolated test-DB selection for T49.2.

```sh
.venv/bin/python scripts/plan_human_knowledge_snapshot.py --check
```

The existing report is immutable:repeat `--run` refuses it. This PLAN is not SQL ingestion
authorization and does not lift the original family projection's `postgresql_ingestion` exclusion.

## Docker and PostgreSQL status

The default offline Compose service is runtime-verified on Docker Desktop 29.5.3/aarch64 with
Python 3.12.14. The image ran as non-root `pvr` (UID 100), kept its root filesystem read-only,
used `/tmp` as its writable tmpfs, published only `127.0.0.1:8000`, and reached healthy readiness.
QA exercised the UI assets, all three decision states, default debug omission, request IDs, and a
dedicated missing-catalog container that failed closed with health/resolve 503 and no identity.

```bash
docker compose config --quiet
docker compose build api
docker compose up --wait api
curl --fail http://127.0.0.1:8000/health
docker compose down
```

The installed `pvr-report` CLI is also verified inside the rebuilt read-only Python 3.12 image. It
generated and validated JSON, Markdown, and four SVG files under writable `/tmp`:

```bash
docker compose run --rm --no-deps api \
  pvr-report --output-directory /tmp/pvr-report
```

The report CLI's in-process ASGI samples still record `container.measured=false`; real
host-to-container timing is a separate artifact. On the same single arm64 machine, 50 sequential
loopback requests after 10 warm-ups produced nearest-rank p95 **`4.721208 ms`** at concurrency 1.
The measurement includes the host HTTP client, Docker Desktop port forwarding, Uvicorn/FastAPI,
the offline resolver, and JSON serialization/parsing. It excludes startup, TLS, reverse proxy,
remote networking, concurrent load, and PostgreSQL, so it is not production latency evidence. See
the [raw runtime artifact](reports/runtime-validation/docker-python312-http-latency.json).

An optional `postgres` profile defines pgvector, Alembic migration, and canonical-catalog
ingestion services:

```bash
docker compose --profile postgres up -d --wait postgres
docker compose --profile postgres run --rm migrate
docker compose --profile postgres run --rm ingest
docker compose --profile postgres run --rm materialize
docker compose exec postgres psql -U pvr -d pvr \
  -c 'SELECT COUNT(*) FROM product_embedding;'
PVR_BACKEND=postgres docker compose --profile postgres up -d --wait api
docker compose --profile postgres down
```

The first `ingest` run writes all 120 fixture variants plus aliases, identifiers, provenance,
full-text source documents, and version metadata in one transaction. `materialize` deterministically
encodes the same 120 catalog documents into versioned 192-dimensional vectors and stores them in
pgvector. Repeating either operation with the same catalog leaves the logical rows unchanged.
Identity or identifier collisions roll back the entire ingestion attempt. `docker compose
--profile postgres down` keeps the named local volume; adding `-v` deletes that volume and its data.

The default remains the fully offline Dual-RAG runtime. Setting `PVR_BACKEND=postgres` moves both
canonical candidate sources to the database: PostgreSQL FTS supplies sparse candidates and exact
pgvector cosine distance supplies dense candidates. Startup validates catalog and embedding
versions, checksums, identities, and row counts. Human-knowledge retrieval remains a separate
non-canonical source.

## Limitations

- `fixture-v1` is synthetic/curated. The numbers do not establish production accuracy, broad Hot
  Wheels coverage, or production readiness.
- `hashing-v1` is a deterministic baseline, not a neural embedding model. No pinned external
  embedding or cross-encoder artifact was integrated or evaluated.
- The verified PostgreSQL sparse+dense path covers one local arm64 machine, 120 fixture products,
  and sequential smoke requests. TLS, proxying, remote networking, concurrent load, PostgreSQL
  latency at 3,000 rows, approximate vector indexes, and external models were not measured.
- Runtime dependencies use bounded ranges plus a selective Python 3.12 constraints file, not a
  complete transitive lock. PostgreSQL extras and build dependencies may still resolve differently
  in a future build. `pvr-report` requires runtime `httpx2>=2,<3`.
- UI behavior was verified with a Node DOM harness, not a live browser.
- Architect, security, and performance-agent reviews were deferred under Lite/MVP Mode. The local
  loopback debug endpoint needs access control or disabling before non-local exposure.

Decision history and remaining debt are recorded in
[MVP decisions](docs/decisions/product-variant-resolver.md) and the
[project log](docs/PROJECT-LOG.md).
