# Project Log

## 2026-09-06 — Conservative alignment exposes the real catalog-coverage gap

### What was executed and what problem it solves

The newly imported 101-record human-label corpus could not yet participate in canonical resolver
evaluation because the labels had no verified links to this repository's UUIDs. This iteration ran
the requested catalog-alignment step and created a deterministic, reviewable status for every
record. The outcome is 0 canonical mappings, 2 exact casting-family-only matches, and 99 unmapped
records. The two partial matches are `Toyota Supra`; each still has 12 possible synthetic variants,
so neither receives a UUID.

This result identifies the actual constraint rather than hiding it behind a similarity score. The
current fixture catalog contains 10 synthetic casting families, while the human corpus contains 97
real casting names. The next accuracy bottleneck is catalog coverage and variant provenance, not
the mechanics of matching the two JSON files.

### Code and data changes, with reasons

`scripts/align_human_labeled_names.py` builds
`data/human_labeled_catalog_alignment.json` plus a checksum manifest. Each row retains its human
name fields, alignment status, reason, nullable canonical identity, matched family, and possible
canonical IDs. Exact Unicode/punctuation-normalized brand and casting are required for a family
match. A UUID additionally requires exact series and one variant discriminator—color, edition, or
rarity tier—to reduce the family to one unique product.

Fuzzy string matching was intentionally excluded from label creation. It would be useful as a
retrieval signal, but unsafe as ground truth: for example, `Dodge Challenger` versus `Dodge
Charger`, a chassis-specific Skyline versus a generic Skyline family, or a real 2000 Chevy Nomad
versus synthetic 2022/2023 variants can look textually close while representing different product
identities. The conservative policy allows those items to remain visible as unmapped instead of
silently assigning an incorrect UUID.

`scripts/validate_fixture_data.py` now verifies the alignment checksum, source dataset checksum,
catalog checksum, complete case-ID coverage, status values, and UUID/slug integrity. Five focused
tests cover the current 0/2/99 result, the 12-candidate Toyota Supra families, null identities for
unmapped rows, frozen inputs/output, and deterministic regeneration. R18 and completed task T27
were added to the Lite brief; README, QA review, decision D9, and the AI-eval evidence document now
state that this is a catalog-coverage measurement rather than an accuracy result.

### Technical choice and next decision

The method uses standard-library normalization and exact structured fields instead of adding an
embedding model or fuzzy-matching dependency. This keeps the alignment deterministic, auditable,
and appropriate for the Lite workflow. The trade-off is deliberately low automatic coverage: it
prefers a review queue over false canonical labels.

The next data task should not weaken the threshold. It should define how reviewed names become a
separately versioned, human-backed catalog: deduplicate repeated scans, settle whether series and
variant fields describe the product or marketplace listing, add provenance, mint stable IDs, and
then create a casting-family grouped evaluation split. PostgreSQL ingestion T07 remains valuable,
but loading a broader catalog should follow a clear source-of-truth decision.

### Verification evidence

The alignment command processed all 101 records and reproduced the frozen 0 mapped / 2
casting-family-only / 99 unmapped counts. The central fixture validator passed with both input and
output checksums linked. Five focused alignment tests passed, the complete host suite passed 50/50
with `PYTHONPATH=src`, Python compilation passed, and `git diff --check` reported no whitespace
errors. The existing host TestClient deprecation warning remains an environment/dependency warning
already documented by the project; it did not cause a test failure.

## 2026-09-06 — Human-labeled real-noisy names added as an auxiliary dataset

### What was executed and what problem it solves

The project previously relied on a 100-case synthetic/curated benchmark. That fixture is useful for
proving the resolver architecture, but it does not show how recognition output differs from a
person's verified answer on real noisy scans. This iteration imported the user-approved local
labeling queue into `human-labeled-real-noisy-v1`. The new corpus contains 101 confirmed human
labels: 91 records have both the original top recognition name and the human-verified name, and 10
records preserve the fact that recognition returned no candidate while still retaining the human
answer. Four rows explicitly excluded during the earlier human review were not imported.

This solves two immediate problems. First, future work can measure name cleanup and candidate
selection against real reviewed examples instead of relying only on generated titles. Second,
failed recognition attempts are represented as data rather than disappearing from the sample,
which prevents coverage from looking better simply because empty outputs were dropped.

### Code and data changes, with reasons

`scripts/import_human_labeled_names.py` was added as a deterministic CSV-to-JSON boundary. It
requires the source columns used to distinguish `candidate_1` from `human_expected_candidate` and
the normalized human casting/pricing fields. Included rows must have confirmed human labels;
candidate confidence must be numeric and bounded; duplicate case IDs fail the import. The generated
record uses the explicit fields `initial_name` and `human_label_name`, so a beginner reviewing the
data can see the before/after pair without reconstructing meaning from the old labeling workbook.

The importer writes `data/human_labeled_names.json` and a separate frozen manifest. The manifest
records the source checksum and generated dataset checksum rather than a machine-specific absolute
path. Local frame paths and images were not copied because the current Product Variant Resolver is
a text-first Dual RAG project and the requested evidence is the name pair; omitting those paths also
keeps this repository portable when only the `Product Variant Resolver/` folder is pushed.

`scripts/validate_fixture_data.py` now validates the auxiliary corpus alongside the original
catalog and benchmark. `tests/test_human_labeled_names.py` checks the 101 total records, the 91/10
paired-versus-no-candidate split, confirmed human labels, unique IDs, checksum integrity, and the
declared evaluation exclusions. The MVP brief adds R17 and completed task T26, while the QA review,
README, decision record, and AI-eval evidence explain the data boundary and its limitations.

### Technical and method choices

JSON was selected as the checked-in runtime format because the existing project already uses
versioned JSON fixtures and can validate them with Python's standard library. Keeping XLSX as the
runtime source would add spreadsheet parsing dependencies and make automated validation harder;
copying the CSV would retain many source-only workflow columns and local frame paths that this
project does not need. A deterministic importer preserves the option to regenerate the compact
artifact from the original review queue while allowing GitHub users to inspect the resulting data
without the source project.

The real-name corpus was not merged into `benchmark.json`. Those 101 labels describe reviewed
names, but they have not yet been mapped to this repository's immutable canonical UUIDs and slugs.
Using them immediately for canonical accuracy or calibration would turn text similarity into an
unsupported identity claim and risk label leakage. They are therefore limited to candidate-name
evaluation, name-normalization evaluation, and future catalog alignment. Once mappings and a
casting-family grouped split exist, a qualified subset can be promoted into the formal benchmark.

### Verification evidence and remaining limitation

The central fixture validator passed with the new corpus included. Four focused human-label tests
passed, and the complete host test suite passed 45/45 with `PYTHONPATH=src`. Python compilation and
`git diff --check` also passed. A first complete-suite command omitted `PYTHONPATH=src` and therefore
could not import the package; rerunning with the repository's documented module path passed, so
that attempt is recorded as an invocation error rather than a product failure.

Targeted Ruff and mypy were not rerun in this host interpreter because those optional development
modules are not installed. An offline `uv` attempt could not access its external cache under the
workspace sandbox. The added code is covered by compilation and behavioral tests, but static-tool
verification should be repeated in the pinned development or Docker QA environment before a later
release claim expands beyond this Lite data milestone.

## 2026-09-01 — Lite/MVP fixture implementation and handoff

### Context, problem, and observable outcome

This iteration ran in **Lite / MVP Mode**. The starting specification described a production-shaped
resolver—catalog-backed identity, hybrid retrieval, reranking, calibrated abstention, an API, and a
reproducible benchmark—but the useful first delivery had to be demonstrable without claiming that
PostgreSQL, pgvector, external models, or a real marketplace catalog already worked. The engineering
problem was therefore twofold: build a complete resolution loop that could run offline, and make
every resulting claim traceable to a frozen fixture and an explicit runtime boundary.

The delivered offline path now accepts a noisy title, extracts generic syntax and catalog-derived
hints, retrieves candidates through sparse, dense, and structured signals, fuses them with RRF,
calibrates the leading candidate, and returns `matched`, `ambiguous`, or `no_match`. FastAPI exposes
that path through `/resolve` and `/health`; the default response omits internal evidence, while
`debug=true` returns bounded signals, ranks, conflicts, model versions, and stage timings. The
observable result is a versioned `fixture-v1` report over 21 synthetic test cases rather than an
unsupported production claim: Recall@25 and Top-1 are `1.0`, hard-negative accuracy is `1.0` (4/4),
precision is `1.0`, false-match rate is `0.0`, and coverage is `0.8333`.

Focused re-verification exposed three places where the implementation and its claims needed to be
tightened. First, series text needed to be treated as catalog knowledge, not an application-coded
rule, and a wrong series needed to remain a visible soft conflict rather than filter out the correct
candidate. Second, the heuristic reranker had been available in the pipeline without evidence that
it improved the fused ranking. Third, latency needed an HTTP-level measurement and an explicit
statement of what that measurement excluded. After correction, catalog-provided series values
produce `series_hints`; a target with a conflicting series remains in the top 25 and records
`structured_conflicts=["series"]`; RRF and the heuristic reranker both score Top-1 `1.0` on the same
12 matched frozen-test cases; and the report retains warmed in-process ASGI samples while stating
that Docker, TCP, reverse proxy, database, and concurrency were not measured.

### Implementation trace

The implementation was organized by pipeline responsibility so that each claim has a narrow code
and test surface:

- `data/`, `scripts/generate_fixture_data.py`, and `scripts/validate_fixture_data.py` establish the
  frozen catalog, benchmark, grouped split metadata, checksums, provenance, and fixture validators.
  This was necessary to make evaluation reproducible and to prevent synthetic data from being
  presented as scraped marketplace truth.
- `src/product_variant_resolver/{identity,catalog,ingestion}.py` defines immutable UUID/slug
  behavior, normalized catalog records, and idempotent in-memory ingestion.
  `src/product_variant_resolver/{signals,schemas}.py` keeps syntax
  extraction typed and generic. The series correction was implemented through the catalog-derived
  vocabulary assembled in `src/product_variant_resolver/service.py`, passed into
  `extract_signals`, and represented as
  `series_hints`; no Hot Wheels series branch was added to application code.
- `src/product_variant_resolver/retrieval.py` contains the token sparse baseline, deterministic
  `hashing-v1` dense baseline,
  structured match/conflict features, RRF, and fail-closed retrieval orchestration. Series joins
  year, color, collector number, and series position as a soft structured feature so conflicting
  evidence remains inspectable instead of destructively pruning a candidate.
- `src/product_variant_resolver/{rerank,service,config}.py` provides the pointwise interface, optional
  `heuristic-v1` implementation, pipeline assembly, and runtime selection. `reranker_enabled`
  defaults to false; when disabled, debug and health metadata report `disabled` instead of implying
  that a reranker ran.
- `src/product_variant_resolver/{calibration,policy,training}.py` implements logistic calibration,
  train-only model
  fitting, dev-only threshold selection, artifact/version checks, and the three-state decision
  policy. Training and evaluation both use the same catalog-derived color and series vocabulary,
  avoiding a mismatch between runtime and offline scoring.
- `src/product_variant_resolver/{api,observability}.py` and `ui/` supply structured request
  validation, error mapping,
  readiness, request correlation, privacy-safe logging, stage timings, and the minimal debug UI.
  API-provided strings are rendered as text, and raw titles are not placed in resolution logs.
- `src/product_variant_resolver/{evaluation,reporting}.py`,
  `scripts/generate_evaluation_report.py`, and `reports/fixture-v1/` preserve raw ranks, decision
  counts, latency samples, derivations, configuration, disclaimers, and SVG summaries. Reporting
  now records `selected_default="rrf"`, the exact reranker gain,
  whether an external cross-encoder was evaluated, and whether container latency was measured.
- `tests/unit/`, `tests/integration/`, `tests/api/`, `tests/evaluation/`, and `tests/ui/` cover identity,
  parsing, soft conflicts, fusion, calibration/policy guards, three-state resolution, fail-closed
  behavior, report disclosures, and UI rendering. `migrations/`, `Dockerfile`, and
  `docker-compose.yml` preserve future persistence/deployment boundaries, but their presence is not
  counted as runtime verification.

### Technical choices, alternatives, and trade-offs

The default retrieval path uses deterministic token overlap plus `hashing-v1` vectors because both
run offline and make the fixture loop reproducible. The specification's PostgreSQL FTS and exact
pgvector path remains the intended scalable alternative, while a pinned sentence-transformer is the
intended semantic alternative. The trade-off is deliberate: the current baselines have low setup
cost and fail no external dependency, but `hashing-v1` is not a neural embedding and the measured
fixture accuracy cannot establish semantic recall on real marketplace titles.

RRF was chosen over direct addition of sparse and dense scores because the component scores live on
different scales, while RRF needs only ranks and remains deterministic. Weighted score fusion could
eventually learn more domain-specific signal weighting, but it would add tuning risk to a 100-case
synthetic benchmark. Structured attributes therefore contribute explicit matches and conflicts
without becoming hard filters, preserving recall when seller titles contain an incorrect year,
color, or series.

Calibration and abstention were retained instead of an always-pick-Top-1 policy because an entity
resolver must refuse weak or near-tied evidence. The calibration model is fit on grouped train data,
thresholds are selected on grouped dev data, and test labels are held for final evaluation. This
adds artifact and policy-version management, but it makes `ambiguous` and `no_match` first-class
outcomes and exposes the precision/coverage trade-off.

The pointwise reranker underwent an explicit **selection reversal**. Before the frozen comparison,
the architecture allowed the local heuristic after RRF as a normal pipeline stage. Catalog-derived
series handling then strengthened the generic retrieval and structured evidence, and the same 12
matched test queries produced Top-1 `1.0` for both RRF and `heuristic-v1`. The measured absolute gain
was therefore `0.0`, below the R11 `0.05` value gate. After that evidence, the runtime default was
changed to RRF, the heuristic became an opt-in/offline ablation via
`PVR_RERANKER_ENABLED=true`, and calibration/policy versions were aligned with the RRF path. This
avoids paying for and explaining an unproven stage while preserving a replaceable pointwise
interface. No external cross-encoder was evaluated, so this decision does not predict whether a
pinned neural reranker would help on real hard negatives.

### Verification evidence

Final QA recorded **PASS WITH RISKS** for the dependency-light fixture path. The available unit,
integration, API, UI harness, fixture, training, evaluation, and reporting suite passed 38/38;
Python compilation and fixture validation passed; calibration and dev-selected policy artifacts
were regenerated with `test_labels_accessed=false`; and both default and PostgreSQL-profile Compose
configurations passed static validation. Manual API checks observed all three decision states,
default debug omission, bounded debug candidates, structured validation failures, and fail-closed
responses for a missing catalog, PostgreSQL backend selection, unavailable external providers, and
a simulated retriever failure.

The frozen data evidence is `fixture-v1`: 120 products and 100 benchmark cases (`60 matched`,
`20 ambiguous`, `20 no_match`) across 14 casting families and 30 near-duplicate groups. Families
occur in exactly one query split, and the catalog and benchmark SHA-256 values match
`data/manifest.json`. The checked-in report evaluates exactly 21 synthetic test cases, including 12
matched cases, and retains the raw counts used by every headline metric.

Latency evidence is intentionally bounded. The latest checked-in report records internal-pipeline
p95 `1.5525 ms` and warmed in-process HTTP/ASGI p95 `7.9523 ms`, each over 21 sequential samples
after five excluded warm-up requests at candidate K=25. A separate fresh QA regeneration recorded
HTTP/ASGI p95 `2.45 ms`; both remain below the 1500 ms fixture smoke budget. These numbers include
FastAPI middleware, validation, dispatch, serialization, and response headers only for the
in-process boundary. They do not include Docker/container startup or execution, TCP/network,
PostgreSQL, a reverse proxy, concurrency, or load, and must not be reported as production latency.

Traceable sources are the [MVP brief](../specs/product-variant-resolver/mvp-brief.md),
[final QA review](../specs/product-variant-resolver/review.md),
[versioned report](../reports/fixture-v1/evaluation-fixture-v1-test.md), and
[MVP evidence](evidence/product-variant-resolver-mvp.md).

### Incomplete work, risks, and next step

The offline fixture path is demonstrable, but the original technology scope is not complete.
`PostgresRetrieverAdapter.execute_ranked` remains unimplemented; Alembic migration cycles,
PostgreSQL ingestion, FTS, exact pgvector retrieval, and live database failure behavior were not
run. The verified dense provider is `hashing-v1`, and the verified optional reranker is
`heuristic-v1`; no pinned external embedding model or cross-encoder, license/checksum, or local
model-cache flow was exercised. Selecting those unavailable providers correctly fails readiness,
but that is not equivalent to implementing them.

Docker received static configuration checks only because the daemon was unavailable. Image build,
container health, read-only filesystem behavior, Alembic execution, and the project-pinned Python
3.12 runtime remain unverified; host QA used macOS arm64 with Python 3.14.6. The UI was exercised
through a Node DOM harness rather than a live browser, post-start readiness transition is not yet
covered, the Starlette TestClient deprecation warning remains, and no formal architect, security,
or performance-agent review was performed.

The next highest-value step is to run the existing default stack in Docker on Python 3.12 and
capture container/TCP health and latency evidence without weakening the current disclaimer. If the
repository will claim PostgreSQL/pgvector or neural models as executable features, implement and
integration-test those adapters next; otherwise keep them explicitly deferred. Real catalog data
and marketplace-derived hard negatives are required before revisiting semantic retrieval,
reranking, calibration, or production-accuracy claims.

## 2026-09-01 — Docker/Python 3.12 runtime milestone

### Context, problem, and observable outcome

The preceding handoff had only static Docker Compose validation. The daemon was unavailable during
that QA pass, so the documentation correctly treated image construction, Python 3.12 execution,
container readiness, filesystem restrictions, real port forwarding, and the installed reporting
CLI as unverified. That was the largest remaining gap in the default offline MVP: source-level and
in-process evidence existed, but a user still could not point to a successful build-and-run record
for the shipped container.

This milestone closes that gap for the **default offline runtime**. A no-cache image build ran on
Docker Desktop 29.5.3/aarch64, installed the project on Python 3.12.14, started healthy as non-root
user `pvr` (UID 100) with a read-only root filesystem and writable `/tmp` tmpfs, and exposed only
the loopback-bound API port. From the host, health, UI assets, `matched`, `ambiguous`, and
`no_match` flows were observable; default responses omitted debug data and carried request IDs. A
separate missing-catalog container returned health and resolve 503 without asserting an identity.
The installed `pvr-report` command also generated and validated its JSON, Markdown, and four SVG
artifacts inside the rebuilt read-only image.

### Implementation trace

The runtime work added `scripts/measure_http_latency.py` to give host→container timing a dedicated,
repeatable measurement path instead of reusing the in-process TestClient numbers. Its output,
`reports/runtime-validation/docker-python312-http-latency.json`, freezes the boundary, environment,
warm-up/sample counts, percentile method, summary, raw samples, request payload, and explicit
inclusions/exclusions. Keeping this result separate from `reports/fixture-v1/` prevents the fixture
evaluation report's in-process ASGI latency from being mistaken for a container measurement.

`pyproject.toml` added `httpx2>=2,<3` to runtime dependencies. The reason is operational rather than
test-only: the installed `pvr-report` entry point directly uses FastAPI TestClient when it generates
HTTP samples. The runtime image therefore needs the compatible client library even when development
extras are not installed. The Dockerfile and default Compose configuration did not need a new
product architecture; the milestone exercised their existing non-root, read-only, tmpfs,
loopback-port, and healthcheck settings and captured evidence that those settings work together.

### Technical choices, alternatives, and trade-offs

Host→container latency is measured with a small standard-library HTTP script rather than folding a
live socket test into the fixture evaluator. This keeps the artifact dependency-light and makes the
boundary explicit: host `urllib`, Docker Desktop port forwarding, Uvicorn/FastAPI, resolver work,
and JSON serialization/parsing are included. An in-container TestClient benchmark would be faster
and more deterministic but would skip port forwarding; a full load tool behind TLS and a proxy
would be closer to production but would add infrastructure and concurrency questions outside this
Lite milestone. The selected sequential, concurrency-1 loopback smoke is therefore useful for
runtime verification, not capacity planning.

For reporting dependencies, alternatives included putting `pvr-report` behind a separate extra or
image, rewriting its HTTP measurement to avoid TestClient, or leaving the HTTP client in the dev
extra. Keeping `httpx2` in runtime dependencies makes the already-shipped CLI usable in the default
image with the smallest code change. The trade-off is a larger runtime dependency surface and
weaker rebuild reproducibility because versions are bounded but not locked.

### Decision changes

Before this milestone, Docker/Python 3.12 was documented as unverified and T23 remained partial;
only Compose syntax had passed. After the successful build, health/UI/three-state flow,
missing-catalog failure, filesystem/user checks, and host→container measurement, the default
offline Docker runtime is now an evidenced deliverable and T23 is complete for that Lite boundary.
This does not promote the optional PostgreSQL profile into a working resolver path.

QA also found that the reporter's HTTP client could not be treated as merely a development concern:
`pvr-report` is installed in the runtime image and invokes TestClient directly. The prior dependency
boundary therefore did not guarantee a usable shipped CLI. After moving the compatible client to
runtime requirements, a no-cache rebuild resolved FastAPI 0.141.1, Starlette 1.6.0, httpx2 2.12.0,
and httpcore2 2.12.0; `pvr-report` then produced all six expected artifacts under the read-only,
non-root constraints. The repository still has no lockfile or constraints file, and the dev extra
still lists legacy `httpx`, so this is a runtime-boundary correction rather than complete dependency
reproducibility.

### Verification evidence

The verified image was `product-variant-resolver:lite` with image ID
`sha256:f5df8cba0c0abaae77b1e01be9269cdbef2dd874be5b168da47aed5d365cc739`.
Docker reported version 29.5.3/aarch64; the container reported Python 3.12.14, UID/GID
`100(pvr)/101(pvr)`, `ReadonlyRootfs=true`, and a healthy loopback publication at
`127.0.0.1:8000`. `/app` was not writable and `/tmp` was writable. Container compile passed with
bytecode directed to `/tmp`; mounted API tests passed 8/8 and reporting tests passed 2/2. Earlier
runtime runs also passed 10 unit, 7 integration, 4 evaluation-metric, and 5 fixture tests, while
direct container evaluation retained Recall@25 `1.0`, Top-1 `1.0`, hard-negative accuracy `1.0`,
precision `1.0`, coverage `0.8333`, and false-match rate `0.0`.

The checked-in [Docker latency artifact](../reports/runtime-validation/docker-python312-http-latency.json)
contains 50 finite sequential samples after 10 warm-ups. Sorting those samples and applying the
recorded nearest-rank rule, `ceil(0.95 * 50) - 1`, reproduces p95 **`4.721208 ms`**; median is
`2.7867085 ms` and mean is `3.14272922 ms`. The test used one local macOS arm64 machine,
concurrency 1, loopback, and the offline-memory backend. Container startup, warm-ups, TLS, reverse
proxy, remote network, concurrent load, and PostgreSQL are excluded. This is a runtime smoke result,
not production latency.

The no-cache reporter verification generated exactly one JSON, one Markdown, and four SVG files.
The JSON passed `validate_report_payload`, retained 21 in-process HTTP samples and the exact
21-case synthetic disclaimer, and correctly kept `container.measured=false` because that report's
latency is not the host→Docker artifact. The final [QA review](../specs/product-variant-resolver/review.md)
records R13 as PASS for this limited boundary, R15 as PASS WITH RISK, and R16 as PASS; the full host
suite remains 38/38 green.

### Incomplete work, risks, and next step

The verified boundary is intentionally narrow. PostgreSQL ingestion, FTS, exact pgvector search,
migration-cycle E2E, external embeddings/cross-encoders, TLS, reverse proxy, remote network,
concurrency/load, and post-start dependency failure transitions remain unverified. The runtime
artifact comes from one Docker Desktop arm64 machine and cannot support a production latency or
capacity claim. The UI still lacks a live-browser smoke beyond the Node harness, and no formal
architect, security, or performance-agent review was performed.

Dependency resolution is the next hardening priority. The successful image used compatible bounded
ranges, but no committed lockfile or constraints file ensures the same versions on a future build;
the dev extra's legacy `httpx` also continues to produce a host warning. The next highest-value step
is to freeze or constrain the verified runtime set and reconcile the TestClient dependency across
runtime and development. PostgreSQL/pgvector and external-model adapters should remain explicitly
deferred unless they are implemented and integration-tested before being claimed.

## 2026-09-02 — GitHub publication milestone

### Context, problem, and observable outcome

The publication requirement was narrower than “push the workspace.” The user explicitly wanted
only `Product Variant Resolver/` to become the GitHub repository so that the parent workspace's
`AGENTS.md`, `.codex/` agent configuration, and original `Product Variant Resolver.md` requirement
document would not enter public history. Treating the parent directory as the Git root and relying
on an ignore list would have made that boundary easier to misconfigure and harder to prove after
the fact.

Publication therefore used the existing independent Git repository rooted inside
`Product Variant Resolver/`. That repository already contained two project commits:
`5fef769` (`feat: establish offline product resolver MVP`) followed by `ad9b74a`
(`test: validate Docker Python 3.12 runtime`). GitHub publication completed successfully to the
public repository `MatthewC144/product-variant-resolver` on `main`. The local branch now tracks
`origin/main`, and both pointed to `ad9b74a` when this milestone was verified. The project is
publicly reviewable without placing the parent workspace's agent instructions or source brief in
the published history.

### Implementation trace

No product code was changed to make publication work. The important implementation boundary is the
nested repository itself: `/Users/yuchen/Desktop/resume project2/Product Variant Resolver/.git`
owns only the project subtree, while the outer workspace remains outside that repository. The
tracked-file inventory begins with project-owned files such as `.dockerignore`, `.env.example`,
`.gitignore`, `Dockerfile`, `README.md`, configuration, fixture data, evidence, migrations, source,
tests, and UI assets. A history-wide name check returned no tracked `AGENTS.md`, `.codex/` path, or
parent-level `Product Variant Resolver.md` requirement document.

The repository remote is the credential-free HTTPS URL
`https://github.com/MatthewC144/product-variant-resolver.git` for both fetch and push. The local
`main` branch was published and configured to track `origin/main`. This project-log entry records
the publication workflow and its safety boundary; it does not copy any outer workspace content into
the repository.

### Technical choices, alternatives, and trade-offs

An independent subdirectory repository was selected over initializing Git at the parent workspace
and maintaining a large exclusion list. A parent repository plus `.gitignore` could also publish a
single project, but one missed pattern or later `git add -f` could expose orchestration files. A
subdirectory Git root makes the intended scope structural: normal Git commands cannot stage parent
files because they are outside the work tree. The trade-off is operational discipline—contributors
must run Git commands from this repository or explicitly pass its path, and parent-workspace tooling
must not be assumed to manage this history.

HTTPS was retained for the remote rather than placing a personal token in the URL or repository
configuration. The GitHub plugin was useful for verifying the authenticated account
`MatthewC144` and the public target repository, but it did not expose a create-repository
capability. The local `gh` token was also no longer valid. Alternatives were to renew CLI
authentication, switch to SSH after configuring a key, or wait for a plugin capability change.
For this one-time bootstrap, the smallest authorized path was for the user to create an empty
public repository in GitHub and then let standard Git publish the already-prepared local history.
This added one manual step but avoided inventing unsupported plugin behavior or placing credentials
in project files.

### Decision changes

The initial automation preference was to create and publish the repository through an available
GitHub integration or the local `gh` CLI. Capability and authentication checks changed that plan:
the plugin could validate the GitHub identity and repository state but could not create a
repository, while the local CLI credential could not authorize creation. Continuing with either
path would have required new authentication authority or an unsupported operation.

After that evidence, repository creation was split from code publication. The user created the
empty public `MatthewC144/product-variant-resolver` repository; the local independent repository
then added the clean HTTPS remote and performed the first push to `main`. This preserved the
subfolder-only history and avoided expanding the agent's credential or repository-creation
authority. Now that `origin` exists and `main` tracks `origin/main`, future releases do not need the
create-repository capability; they use the normal reviewed commit-and-push workflow.

### Verification evidence

The GitHub plugin verified the signed-in account as `MatthewC144` and the destination as the public
repository `MatthewC144/product-variant-resolver`. Local Git independently showed:

- `origin` fetch and push URLs are both
  `https://github.com/MatthewC144/product-variant-resolver.git`;
- the active branch is `main`, configured as `[origin/main]`;
- `HEAD`, `main`, and `origin/main` resolved to `ad9b74a` after the successful first push;
- the two published commits were `5fef769` and `ad9b74a`, in that order; and
- `git ls-files` plus a history-wide path-name search found no `AGENTS.md`, `.codex/`, or parent
  `Product Variant Resolver.md` content in tracked history.

The first push completed successfully, and the local working tree was clean before this
post-publication documentation entry was added. The remote URL contains no embedded token. This
milestone did not rerun application tests because publication did not change product behavior; the
quality and Docker evidence remain attached to the two published commits and the preceding log
entries.

### Incomplete work, risks, and next step

The GitHub plugin still cannot create repositories, and the local `gh` credential remains
unusable until the user deliberately reauthenticates it. Neither limitation blocks routine work on
the existing `origin`, but a future repository bootstrap must again use an explicitly authorized
creation path. The project is public, so future commits must continue to avoid credentials,
machine-local files, external private data, and parent-workspace instructions. Publication does not
change the previously documented product limitations around synthetic fixtures,
PostgreSQL/pgvector, external models, or production readiness.

For future remote updates, begin inside `Product Variant Resolver/`, confirm
`git rev-parse --show-toplevel` resolves to that directory, inspect `git status` and the staged
diff, and repeat the tracked-path check for `AGENTS.md`, `.codex/`, and the parent requirement file
before committing. Push ordinary reviewed commits to `origin main`, then confirm local `main` and
`origin/main` agree. Do not initialize or publish the parent workspace, embed tokens in remote URLs,
or use force-push as a routine update mechanism. Documentation changes made after the initial
two-commit publication, including this milestone record, should follow that same review, commit,
push, and remote-verification sequence.

## 2026-09-06 — Quantity `x` token-boundary correction

### Context, problem, and observable outcome

While reviewing the signal-extraction stage, a concrete false positive was reproduced from the
title `box12 Nomad`: the quantity expression treated the trailing `x12` inside the word `box12` as
an independent quantity marker. `extract_signals()` therefore returned `quantity=12` and
`multipack_hint=true`, even though the title did not contain a quantity token. This could distort
the structured evidence passed into retrieval and make an ordinary single-product title look like
a multipack.

The correction narrows only the `x` quantity syntax. After the change, an `x` must begin outside a
word, so `box12` is no longer interpreted as a quantity while the intentionally supported forms
`x12` and `x 12` continue to produce quantity 12. The observable behavior is therefore more
precise without removing the compact marketplace notation that the resolver already accepted.

### Implementation trace

The regression was captured first in `tests/unit/test_identity_signals.py`. The new coverage
asserts both sides of the contract: the embedded substring in `box12 Nomad` must not produce a
quantity or multipack hint, while standalone `x12` and `x 12` remain valid. Writing the failing
test before the fix preserved the original defect as evidence and prevented a narrow correction
from silently breaking supported input.

The product change is confined to the quantity pattern in
`src/product_variant_resolver/signals.py`. Only the `x` branch of `QUANTITY_RE` changed, gaining the
negative lookbehind `(?<!\w)`. No retrieval, ranking, calibration, policy, API, or catalog behavior
was modified. This limited scope matches the root cause: the extractor lacked a left token
boundary for one syntax branch rather than having a broader quantity-parsing design failure.

### Technical choices, alternatives, and trade-offs

The selected boundary, `(?<!\w)x`, rejects an `x` immediately preceded by a Unicode word
character while still accepting `x12`, `x 12`, and an `x` preceded by punctuation or whitespace.
It was chosen as the smallest rule that describes the intended semantic distinction: `x` is a
quantity marker only when it starts a token-like expression, not when it is part of an existing
word.

A simple whitespace requirement was considered conceptually but would be unnecessarily strict:
marketplace titles can place compact quantity markers after punctuation or at the beginning of a
title. A broader parser or post-match tokenization layer could offer more control over multilingual
and unusual listing formats, but it would enlarge the change surface without evidence that those
formats are currently required. The accepted trade-off is that this remains a regex-based,
English-oriented heuristic rather than a general quantity grammar.

### Decision changes

The earlier quantity rule implicitly allowed the `x` marker at any character position. Review
evidence from `box12 Nomad` showed that this permissive behavior was not merely theoretical: it
produced a false structured signal and a false multipack hint. The decision was therefore narrowed
from “any `x` followed by digits may indicate quantity” to “only an `x` without a word character on
its left may indicate quantity.”

The supported configuration and public signal schema did not change. Existing `lot of`, `qty`,
`quantity`, and pack-style branches were deliberately left untouched because the reproduced fault
and regression coverage concern only the standalone `x` notation.

### Verification evidence

The responsible implementation run reported that the new unit test failed before the regex change
and passed afterward. Following the correction, the signal-focused unit set passed **6/6**, the
complete `unittest` suite passed **39/39**, and `git diff --check` reported **PASS**. These results
verify the local Python test boundary and patch formatting; they do not add Docker, browser,
PostgreSQL, external-model, or production accuracy evidence.

The test run continued to emit the repository's existing Starlette/httpx deprecation warning. No
new warning was attributed to this change, but the warning remains part of the active dependency
maintenance risk and should not be represented as resolved by the passing suite.

### Incomplete work, risks, and next step

Quantity extraction still recognizes a deliberately small set of English-oriented patterns. This
milestone did not expand coverage for other languages, locale-specific notation, Unicode
multiplication symbols, or additional marketplace-specific quantity formats, and it did not
replace regex extraction with a parser. Those cases remain deferred until real catalog or listing
evidence justifies their complexity.

The highest-value next action is to continue the planned Lite-mode product work while keeping new
quantity formats evidence-driven: when a real false positive or false negative is found, add the
smallest paired regression test before changing the grammar. Separately, the existing
Starlette/httpx deprecation warning should be resolved through the already documented dependency
reconciliation work rather than mixed into signal-extraction changes.

## 2026-09-06 — Python 3.12 dependency contract hardening

### Context, problem, and observable outcome

The Lite runtime had already been exercised with Python 3.12 and Docker, but dependency resolution
was still allowed to drift inside broad version ranges. The immediate symptom was a deprecation
warning during TestClient use. Investigation traced the first cause to the development extra
explicitly installing legacy `httpx`: with Starlette 1.3+/1.6 this allowed TestClient to take its
legacy fallback path even though the project already depended on the current `httpx2` transport.
Removing that duplicate transport exposed a second, independent compatibility warning in a fresh
Python 3.12 environment: AnyIO 4.15.1 deprecated an alias still imported by Starlette 1.6.

The dependency contract is now explicit for the compatibility-sensitive Python 3.12 web stack.
Fresh constrained installation selects one TestClient transport and keeps its import warning-free;
ordinary Docker builds consume the same constraints instead of silently choosing new FastAPI,
Starlette, transport, AnyIO, Pydantic, or Uvicorn versions. This is dependency hardening for the
existing Lite application, not a product-feature or retrieval-behavior change.

### Implementation trace

`pyproject.toml` removed legacy `httpx` from the `dev` extra. Runtime `httpx2` remains because the
installed `pvr-report` command uses FastAPI TestClient, so this was not merely a test-only concern.
The direct dependency declarations continue to express supported ranges; they were not replaced
with exact pins in project metadata.

`constraints/python312.txt` was added as the selective exact-version layer for the validated web
stack: FastAPI 0.141.1, Starlette 1.6.0, `httpx2` 2.12.0, `httpcore2` 2.12.0, AnyIO 4.14.0,
Pydantic 2.13.5, and Uvicorn 0.52.4. `constraints/README.md` explains the scope, local install
command, coupled update procedure, and evidence required before promoting future versions.
`Dockerfile` now uses `python:3.12.14-slim`, copies the constraints directory, and applies
`constraints/python312.txt` through pip's `-c` option while installing the existing PostgreSQL
extra.

`tests/unit/test_dependency_constraints.py` adds executable contract checks rather than relying on
documentation alone. It verifies that every direct runtime dependency is represented in the
Python 3.12 constraints, that Docker applies the constraint file, and that development no longer
installs legacy `httpx` while the selected TestClient transport and AnyIO compatibility pin remain
present.

### Technical choices, alternatives, and trade-offs

A selective constraints file was chosen instead of converting `pyproject.toml` to exact versions.
This preserves normal Python package semantics—direct dependencies still publish bounded supported
ranges—while Docker and reproducible local verification can constrain the small stack whose
versions demonstrably interact. The alternative of leaving only broad ranges was simpler, but a
future install could reproduce either warning or introduce an unreviewed compatibility change.
A complete transitive lock would provide stronger reproducibility, but it would also expand this
Lite milestone into packaging, platform-marker, PostgreSQL, and build-tool resolution work that has
not yet been runtime-validated.

AnyIO 4.14.0 was pinned instead of suppressing the warning or accepting AnyIO 4.15.1. Warning
suppression would hide compatibility drift without removing it, while changing Starlette or the
TestClient transport again would disturb the already validated FastAPI stack. Keeping the known
Starlette 1.6/`httpx2` 2.12 combination and constraining the smallest newly identified edge made
the dependency decision evidence-driven. The fixed Docker patch tag similarly reduces unexpected
Python drift, while deliberately avoiding an architecture-specific digest so the same Dockerfile
continues to support ARM64 and AMD64.

### Decision changes

The first decision was to resolve the TestClient warning solely by removing legacy `httpx` from
development dependencies and relying on the project's existing `httpx2` runtime dependency. A
fresh Python 3.12 install showed that this was necessary but insufficient: once the legacy fallback
was gone, AnyIO 4.15.1 produced a separate alias-deprecation warning through Starlette 1.6. The
decision therefore changed from transport cleanup alone to a coupled, selectively constrained web
stack with AnyIO fixed at 4.14.0.

The runtime-image policy also narrowed from the moving `python:3.12-slim` family to the verified
`python:3.12.14-slim` patch tag, and from unconstrained pip resolution to `pip -c`. These changes do
not claim that every transitive package is locked: PostgreSQL extras and packaging dependencies
remain range-resolved. Future updates must treat Starlette, AnyIO, `httpx2`, and `httpcore2` as a
compatibility set and regenerate evidence rather than changing one pin in isolation.

### Verification evidence

The responsible implementation run created a fresh environment under `/private/tmp` with Python
3.12.13 and installed the project successfully using the new constraints. Importing and using
FastAPI TestClient was warning-free. The full suite passed **41/41** with warnings promoted to
errors via `pytest -W error`; `pip check`, targeted Ruff, targeted strict mypy, Docker Compose
configuration validation, and `git diff --check` all reported **PASS**. Docker Hub manifest
inspection confirmed that the selected `python:3.12.14-slim` base is published for both ARM64 and
AMD64.

This initially proved constrained host installation and the static dependency/Docker contract. At
that point the Docker daemon was not running, so the first record correctly stopped short of
container validation. A subsequent closure run on Docker Desktop 29.5.3 completed
`docker compose build --no-cache api` and produced image
`sha256:e67d64e95abab329c901bdb5946f86962a09dc7217e2048a3b1c0568ec8b9d75`.
The image reported Python 3.12.14, UID/GID `100(pvr)/101(pvr)`, FastAPI 0.141.1, Starlette 1.6.0,
`httpx2`/`httpcore2` 2.12.0, AnyIO 4.14.0, Pydantic 2.13.5, and Uvicorn 0.52.4. A
`python -W error` TestClient import completed without warnings, and legacy `httpx` was absent.

With the repository mounted into a read-only container and writable paths supplied through tmpfs,
the 39 backend/API/evaluation/reporting/integration/unit/fixture tests that do not require Node all
passed. The attempted full 41-test container selection was not a 41/41 pass: the UI controller
test errored because this runtime image intentionally has no Node executable. That is a validation-
environment boundary, not evidence of a UI regression; the fresh constrained host Python 3.12
environment remains the evidence for the complete 41/41 suite. In the same read-only container,
`pvr-report` generated one JSON, one Markdown, and four SVG artifacts successfully. Compose reached
healthy state; inspection confirmed `User=pvr` and `ReadonlyRootfs=true`; live HTTP checks returned
ready health plus the expected `matched`, `ambiguous`, and `no_match` outcomes, with no identity in
the latter two states.

The container closure promotes the exact selected pins from host-only to container-verified for
this Lite offline boundary. It does not change the earlier scope caveats: full-repository Ruff still
reports 36 pre-existing findings, and whole-repository mypy debt also remains outside this focused
dependency check.

### Incomplete work, risks, and next step

`constraints/python312.txt` is intentionally not a complete transitive lock. PostgreSQL extras,
setuptools/build tooling, platform markers, and indirect packages outside the compatibility-
sensitive web stack may still resolve differently, so this milestone does not establish fully
reproducible builds. It also does not resolve the 36 existing whole-repository Ruff findings or
change the previously deferred PostgreSQL runtime adapter.

The no-cache container closure is now complete for the Lite offline path. The next dependency
decision is deferred until the PostgreSQL runtime path is implemented: at that stage, evaluate a
complete transitive lock that includes its extras and repeat the same constrained build/runtime
evidence. Until then, the selective constraints must not be described as a complete lock, the
runtime image must not be expected to execute Node-based UI tests, and the existing whole-repository
Ruff/mypy findings remain explicit maintenance debt.

## 2026-09-06 — T04 PostgreSQL/pgvector migration-cycle verification

### Context, problem, and observable outcome

T04 already had an Alembic `0001` migration describing the PostgreSQL/pgvector catalog schema,
but the repository did not yet contain runtime evidence that a new database could apply it,
reverse it, and apply it again without schema drift. The task therefore closed the verification
gap rather than redesigning the database: the existing migration schema required no changes.

An isolated PostgreSQL 16/pgvector database now completed the full
empty → upgrade `0001` → downgrade `base` → upgrade `0001` cycle. Both upgraded states were
inspected and found equivalent. The observable result is a reproducible T04 check that verifies
the seven application tables, their identity and integrity constraints, the required indexes and
specialized PostgreSQL types, the `vector` extension, and final Alembic revision `0001`.

### Implementation trace

`scripts/verify_postgres_migration.py` was added as the executable verification boundary. Before
making any migration change it requires an empty application schema, then drives Alembic through
the complete cycle and inspects PostgreSQL metadata after each upgrade. The runner asserts all
seven application tables; their primary keys; the required product, alias, and identifier unique
constraints; the complete normalized release-year expression; and each cascade foreign key from
its source column to `product_variant.canonical_uuid`. Index checks bind table, index name, access
method, ordered columns, and column order rather than accepting a name/method match alone. The
runner also verifies `product_search.search_document` as `tsvector`,
`product_embedding.embedding` as `vector(192)`, removal of the application tables after
downgrade, and final database revision `0001`. Alembic's `script_location` is resolved to an
absolute repository path so execution does not depend on the caller's working directory.

`Dockerfile` now includes this runner so the verification can execute from the same constrained
project image used by the repository. `.dockerignore` was narrowed only enough to allow
`scripts/verify_postgres_migration.py` into that build context; other scripts remain excluded.
The existing `migrations/versions/0001_initial_catalog.py` schema was left unchanged because the
runtime assertions matched its intended contract. No API, resolver, fixture, retrieval, or
calibration code changed as part of T04.

### Technical choices, alternatives, and trade-offs

A committed, fail-fast runner was selected instead of documenting only a sequence of manual
Alembic and `psql` commands. Manual commands could demonstrate one successful attempt, but they
would leave important checks dependent on operator memory and make the downgrade/second-upgrade
comparison difficult to repeat consistently. The runner turns the intended migration contract
into executable assertions and produces a structured result that a future developer or CI job can
re-run against a disposable database.

The accepted trade-off is deliberate strictness: this runner is for isolated, empty databases and
refuses to operate when application tables already exist. It is not a general database diagnostic
or an upgrade tool for developer or production data. The empty-schema guard deliberately inspects
application tables, not every possible schema object, so it must still be paired with a disposable
database rather than treated as a universal safety detector. Schema assertions use PostgreSQL
catalog and SQLAlchemy inspection rather than adding a second migration framework. No
approximate-nearest-neighbor index was added because T04 only establishes the schema and the
planned T10 path requires exact pgvector retrieval at MVP scale; an ANN structure would add
maintenance and tuning without a current acceptance requirement.

### Decision changes

The prior project record treated PostgreSQL migration cycling as deferred because only migration
files and static Compose configuration had been reviewed. Runtime evidence from the isolated
cycle now promotes T04 itself to complete: the database can be created, downgraded, and recreated,
and the resulting constraints, indexes, types, extension, and revision are explicitly checked.
This does not promote the broader PostgreSQL resolver path, because ingestion and retrieval remain
separate tasks.

The downgrade policy intentionally removes the application schema while leaving the `vector`
extension installed. Extensions can be shared by other schemas or applications in the same
database, so automatically dropping it would create a wider destructive boundary than T04 needs.
Consequently, the runner checks that application tables are gone after downgrade but does not
misrepresent retention of the shared extension as a failed rollback.

QA follow-up initially identified three ways a schema check could pass too loosely: indexes could
match without proving their ordered columns, foreign keys could match without proving their target,
and the release-year check could be accepted from partial numeric fragments. The runner was
narrowed to compare complete index tuples, complete source/target/delete-action foreign-key tuples,
and the normalized full check expression. The absolute Alembic script path additionally removes a
working-directory assumption. Re-execution closed these verification risks without changing the
`0001` migration itself.

### Verification evidence

The responsible implementation run used the isolated Compose project name `pvr-t04` and host port
`55432`, keeping the verification separate from ordinary project services and local PostgreSQL
ports. It reported a successful empty → upgrade `0001` → downgrade `base` → upgrade `0001` cycle
and passed every schema assertion: seven tables, primary and unique constraints, the release-year
check, fully targeted cascade foreign keys, btree/GIN index definitions including ordered columns,
`tsvector`, `vector(192)`, the `vector` extension, and final revision `0001`. A separate sentinel
safety check created an application table before invocation and confirmed that the runner refused
to migrate or downgrade the non-empty schema. After verification, the temporary container,
network, and volume were removed.

The same implementation run reported **41/41 host tests PASS**, Python compilation of the added
runner and migration sources **PASS**, and `git diff --check` **PASS**. These results support the
migration runner, existing host behavior, and patch integrity. They do not constitute PostgreSQL
fixture-ingestion, sparse-FTS, exact-vector-retrieval, resolver-E2E, production-data, or
concurrent-load evidence.

### Incomplete work, risks, and next step

Creating the `vector` extension depends on database permissions; environments where the migration
role cannot install extensions still need administrator provisioning or a documented preinstall
step. The runner must remain restricted to disposable empty databases because its deliberate
downgrade would remove all application tables. The guard detects existing application tables but
does not inventory views, functions, types, or every other possible object in `public`, and CI does
not yet provision PostgreSQL and run this cycle automatically. Its decision to preserve the shared
`vector` extension also means the cycle does not prove complete database-level teardown. ANN
indexing remains unnecessary for the exact-search MVP and has not been implemented or evaluated.

T07, T09, and T10 remain incomplete: PostgreSQL fixture ingestion, PostgreSQL full-text search,
and exact pgvector retrieval have not been exercised by this milestone. The single highest-value
next action is **T07 — implement idempotent PostgreSQL fixture ingestion**, preserving immutable
canonical IDs and catalog/index version metadata while proving that repeated loads are identical
and invalid or colliding fixtures fail transactionally. Completing T07 will turn the verified
empty schema into a populated, repeatable database foundation for the later retrieval tasks.

## Required format for future entries

Every future project-log entry must preserve the following traceability structure:

1. **Context, problem, and observable outcome:** explain what triggered the work, what was wrong or
   missing, what was executed, and what a caller or evaluator can observe afterward.
2. **Implementation trace:** name the changed modules or file groups and explain why each group
   changed; do not provide only a list of completed tasks.
3. **Technical choices, alternatives, and trade-offs:** record the selected method, viable
   alternatives considered, and the cost or limitation accepted.
4. **Decision changes:** when a choice is reversed or narrowed, record the before/after decision,
   the exact evidence that triggered it, and any version/configuration impact.
5. **Verification evidence:** cite commands/results already produced by the responsible agent,
   frozen data/report versions, raw-count-derived metrics, runtime/hardware, and measurement scope.
   Never upgrade a static check into runtime evidence or a synthetic result into a production claim.
6. **Incomplete work, risks, and next step:** state deferred adapters, unrun environments/reviews,
   known warnings, and the single highest-value next action.

Entries may use a small table or compact list for navigation, but the main record must remain an
explanatory engineering narrative linked to existing specifications, code, QA evidence, or reports.
