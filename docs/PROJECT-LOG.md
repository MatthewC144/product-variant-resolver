# Project Log

## 2026-09-12 — T48.3 turns owner confirmation into a frozen but unscored benchmark

### What was executed and what problem it solves

The previous handoff presented the complete frozen query pack, linked a human-readable review, and
explained that the next step required project-owner confirmation before labels could exist. The
owner's instruction to proceed therefore authorized exactly T48.3 against the unchanged
`26e244c0…4358733` query checksum. This closes the attribution gap between an AI-authored question
and the human-approved relevance expectation that will later score it.

All 105 cases now have a separate project-owner decision with timestamp, approval, reason, and
type-correct expectation. The builder combined those decisions with the frozen questions only after
verifying every checksum and source boundary. The output is a labeled benchmark, but no retrieval
was run: candidates, ranks, scores, aggregate metrics, and PASS/FAIL remain absent.

### Code and artifact changes, reasons, and method selection

`scripts/record_family_retrieval_owner_decisions.py` records the current approval as a reproducible
artifact rather than leaving it only in chat history. The approved query checksum is hardcoded in
the script, so rerunning it after any question change fails immediately. The script also revalidates
the query pack and manifest before constructing decisions; this duplicates a small amount of guard
logic intentionally because attribution must never attach to a stale or widened pack.

Expected labels are derived only from the already adjudicated registry/reference relationship, not
from retrieval output. Positive cases expect their referenced review-family ID. Merge controls
expect the existing human-backed casting ID and explicitly forbid a duplicate family ID. Hold
controls require `expected_materialized=false`. Unrelated controls expect zero candidates. Reasons
are tailored to the case type and, for positives, the challenge style; every item retains
`decided_by=project_owner` and the same second-precision UTC decision time.

`owner-decisions.json` stores 105/105 approvals and is checksum-bound to the prior commit's query
pack. `benchmark.json` joins each frozen question with its separately approved expected branch.
`benchmark-manifest.json` freezes the query, owner decision, registry, projection, human catalog,
and their manifests plus the system-under-test code/version block. The benchmark hash is
`440246fb6a3b38f56fc25c1ec939d53d6cfc4457fed738aad561899325808afd`; its explicit exclusions still
prohibit canonical decisions, calibration, threshold selection, query rewriting, retriever tuning,
release truth, PostgreSQL ingestion, and production-accuracy claims.

Two actual-artifact tests were added. The first reconstructs the official benchmark through the
strict builder, compares both JSON objects exactly, checks all 105 approvals, and asserts that no
candidate/rank/score/metric/verdict fields exist. The second runs the owner-decision and benchmark
`--check` commands and proves all three frozen output hashes remain unchanged. Existing negative
tests continue to reject partial, duplicate, stale, changed, or incorrect labels.

Decision D35 explains why the owner's bounded proceed instruction is sufficient authority here and
why it does not widen scope. The new T48.3 evidence document records hashes, class semantics,
absence of scoring, and the next gate. Specs and README now distinguish a frozen labeled benchmark
from a completed retrieval evaluation.

### Verification, current impact, and next step

Focused validation passes 10/10. The complete repository suite passes 194/194 in 2.203 seconds on
the final tree. Python compilation, owner-decision and benchmark byte reproduction, the configured
100-character code-line check, `git diff --check`, and the repository-root scope check pass. Ruff is
not installed on this host, so no Ruff result is claimed. The suite emits only the known non-failing
Starlette legacy-`httpx` environment warning.

No runtime module, API, canonical catalog, calibration/policy artifact, PostgreSQL row, or existing
resolver result changed. T48.4 is now the only next task: implement the read-only evaluator, retrieve
against the already frozen `human-knowledge-hybrid-v2`, compute the precommitted metrics, and publish
PASS or FAIL without tuning this v1 holdout.

## 2026-09-12 — T48.2 freezes 105 independent queries without looking at retrieval output

### What was executed and what problem it solves

T48.2 created the first official evaluation questions for the 42 family documents added in T47.
The earlier 42/42 smoke test asked the index for each family's exact own name, which proves loading
but not robustness. This task replaces that circular test shape with a separately authored,
one-time holdout: 84 positive queries, 4 merge controls, 7 held-identity controls, and 10 unrelated
zero-overlap controls. Every case is fixed to the test split.

The work was deliberately performed without calling the Human Knowledge retriever, resolve API,
debug UI, or any evaluation runner. Only identity references, existing source files, and the T48.1
static validator were read. Consequently, no candidate, rank, score, or PASS/FAIL observation could
influence how a query was worded. The resulting query pack was then checksum-frozen before labels.

### Code and data changes, reasons, and method selection

`scripts/author_family_retrieval_query_pack.py` preserves the hand-authored query wording in a
deterministic source map keyed by existing review IDs. This extra source file was chosen instead of
manually maintaining a 77 KB generated JSON document: it makes missing IDs, ordering mistakes, and
accidental text edits reproducibly detectable. It does not generate wording from a template and
does not import or instantiate the retriever. The script first verifies its 42/4/7 keys exactly
match the registry, assembles allowlisted case fields, asks the T48.1 validator to reject invalid
content, and only then writes atomically. Its `--check` mode is read-only.

The 42 marketplace cases retain recognizable model identity among realistic condition, card,
colour, year, series, auction, and seller words. Their purpose is to test whether ranking survives
extra marketplace language. The 42 lexical cases were individually composed with abbreviations,
misspellings, number-word substitutions, punctuation removal, or spacing changes and are required
to break the full normalized casting phrase. This two-style decision avoids reporting success on
easy exact-name wrappers while hiding spelling weaknesses.

Bogzilla, Crescendo, Draftnator, and Haulerback are single-token family names. Their lexical cases
use `bogzila`, `crescndo`, `draftn8r`, and `haulerbak`; this intentionally may remove every shared
identity token. The current retriever may fail them, but simplifying them after anticipating failure
would bias the holdout. Merge queries express four already accepted links to human-backed castings.
Hold queries express seven identities that must not become review-family documents. Ten invented
single-token strings were selected only after the validator proved zero overlap with all searchable
tokens in the 142-document corpus.

`query-pack.json` is the official 105-case artifact. `query-pack-manifest.json` freezes its SHA-256
`26e244c04325f7909fb222b6cdd32ee2301253db17f0b8b97cf2f63ac4358733`, exact class/style/group
accounting, authoring declaration, test-only exclusions, catalog/projection inputs, and source-code
checksums. The manifest was built with `--freeze-query-pack` and reproduced with
`--check-query-pack`; neither path reads labels or calls retrieval.

Two tests were added to the T48.1 suite. One loads the actual pack and recomputes every validation
and manifest field while asserting that output/rank/expected-label fields do not exist. The other
runs the authoring and manifest check commands and proves their input hashes do not change. The
human-readable evidence file lists all positive and governance-control queries so the owner can
review semantics without seeing retrieval output.

### Verification, limitations, and next step

Focused validation passes 8/8. It confirms exact 105/84/4/7/10 counts, 42 complete two-style groups,
all control identities, four single-token challenges, sorted unique IDs and queries, broken lexical
phrases, zero unrelated overlap, frozen versions/checksums, absence of retrieval-output fields, and
byte-reproducible authoring/manifest checks. The complete repository suite passes 192/192 in 2.250
seconds on the final tree. Python compilation, the configured 100-character code-line check, and
`git diff --check` pass. Ruff is unavailable on this host, so no Ruff result is claimed. The suite's
only message is the known non-failing Starlette legacy-`httpx` environment warning.

Static rules can prove structure and obvious copying, not whether each noisy query is a fair human
expression of its referenced family. That semantic judgment remains intentionally separate. The
next action is project-owner confirmation of the frozen 105 query/reference pairs. T48.3 cannot
create `owner-decisions.json` or a benchmark until that approval binds the exact hash above, and
T48.4 cannot run retrieval until T48.3 succeeds.

## 2026-09-12 — T48.1 builds the evaluation guardrails before any official query is written

### What was executed and what problem it solves

The project owner's instruction to continue confirmed the T48 Lite requirements, design, and task
order. Work therefore advanced by exactly one bounded task: T48.1. The problem being solved is not
retrieval accuracy yet; it is preventing a future accuracy number from being produced with changed,
leaking, incomplete, or self-approved test data.

A new benchmark builder now separates three events that previously existed only in the design. The
query author can validate and freeze a 105-case query pack without labels or retrieval. A separate
project-owner artifact must then approve every frozen case against the exact query-pack checksum.
Only after both artifacts and all source manifests validate can the script create a labeled
benchmark. This order means editing one query after approval, omitting one decision, or changing the
retriever implementation stops the build before it touches prior output.

No official T48 query was authored during this task. The six tests generate temporary synthetic
fixtures solely to exercise the contract, then delete them. No retriever was called, so T48.2 can
still be performed output-blind and no metric or accuracy result exists.

### Code areas changed, reasons, and decisions

`scripts/build_family_retrieval_benchmark.py` is the new single source of truth for the frozen data
contract. It uses field allowlists rather than accepting arbitrary JSON because additional fields
could silently carry retrieval output, training flags, or unreviewed identity data into the test.
It enforces the exact 105/84/4/7/10 case accounting, both required positive styles for every one of
the 42 accepted families, complete merge/hold coverage, ten unique zero-overlap controls, sorted and
unique case IDs/queries, second-precision UTC attribution, and the declaration that no retriever
output was viewed.

The leakage checks compare normalized query text with approved family names, indexed brand/casting
and alias strings, and existing human-label/initial query text. Lexical cases additionally must
break the full normalized casting phrase and declare a spelling, abbreviation, punctuation, or
spacing challenge. Unrelated controls are checked against the token vocabulary of all 142 current
Human Knowledge documents. Automated equality checks cannot judge whether a paraphrase is
semantically fair, which is why they supplement rather than replace the later project-owner review.

The system-under-test block freezes more than a friendly model name. It records the two data
versions/checksums, `human-knowledge-hybrid-v2`, offline `hashing-v1`, 192 dimensions, RRF constant
60, Top-5 limit, and checksums for the normalization, embedding, and retriever source files. This
decision was made because unchanged JSON with changed Python logic is still a different experiment.
The owner-decision schema separately validates expected IDs by case type: positives target review
families, merges target existing provisional-variant castings and forbid duplicate families, holds
remain unmaterialized, and unrelated cases expect zero candidates.

Output files use a temporary file in the destination directory, flush it to disk, and then use
`os.replace`. Validation finishes before either benchmark output is written. This standard-library
approach was selected over adding a database or schema dependency because the artifacts are small,
version-controlled JSON files and Lite mode benefits from a dependency-free reproducible command.
`--check` compares exact bytes without writing; separate `--freeze-query-pack` and
`--check-query-pack` modes exist because T48.2 must freeze questions before owner labels exist.

`tests/test_family_retrieval_benchmark.py` constructs a complete valid contract only inside
temporary directories. Its negative cases deliberately introduce copied text, retained lexical
phrases, unrelated-token overlap, viewed output, dev-split use, removed PostgreSQL exclusions,
changed RRF parameters, stale query checksums, missing/duplicate approvals, and wrong identity
labels. Sentinel-output subprocess tests prove failure does not overwrite a previous benchmark.
`data/evaluation/family-retrieval-v1/README.md` documents the handoff order while intentionally
leaving the formal query/decision/benchmark files absent.

The confirmed spec status and T48.1 checkboxes were updated, README now distinguishes implemented
guardrails from unmeasured quality, Decision D33 records why query freezing is a separate phase, and
the new evidence record captures the acceptance result and limitations.

### Verification, current impact, and next step

The focused contract suite passed 6/6. The complete repository suite increased from 184 to 190 tests
and passed 190/190 in 2.027 seconds on the final tree. Python compilation and `git diff --check`
passed. Ruff is not installed in this host environment, so no lint result is claimed; the code was
checked for the configured 100-character line limit separately. The suite retains one known
non-failing Starlette legacy-`httpx` environment warning.

This change creates no canonical entity, provisional variant, PostgreSQL row, calibration change,
official evaluation label, or retrieval score. T48.2 is now the only next task: independently author
the formal 105-case query pack, validate and freeze its checksum without running retrieval, and
present that frozen pack for project-owner review before T48.3 can add labels.

## 2026-09-11 — T48 defines how family retrieval will be tested without testing on its own names

### What was executed and what problem it solves

T48 begins with a Lite specification rather than immediately creating a benchmark or changing the
retriever. T47 proved that all 42 accepted review families are present and retrievable when queried
with their own exact names. That result is necessary for wiring, but it cannot answer the product
question the next phase actually cares about: whether noisy marketplace wording still retrieves the
right family and avoids unsafe identities.

The new specification converts that ambiguity into a controlled evaluation. It proposes 105 fixed
test cases: 84 positives covering every family twice, 4 accepted-merge controls, 7 held-family
controls, and 10 unrelated queries. Positive cases are split into marketplace noise and lexical
variation so easy queries with extra seller words cannot hide failures on abbreviations, spacing,
punctuation, or misspellings. Queries must be written and committed before anyone views retriever
output; all labels require a separate project-owner decision file before scoring.

### Files added or changed, and why

`specs/family-retrieval-evaluation/requirements.md` defines sixteen EARS requirements covering the
frozen system under test, output-blind authorship, exact case composition, complete family/control
coverage, non-triviality, owner verification, deterministic manifests, test-only isolation,
read-only scoring, metrics, gates, truthful failure, reports, privacy, and full regression.

`design.md` turns those requirements into an artifact and execution architecture. It separates the
pending query pack, owner decisions, frozen benchmark, evaluator, and report so changing one layer
invalidates downstream checksums rather than silently changing the test. The proposed evaluator
retrieves before it reads expected labels and writes ordered candidate/rank evidence from which all
aggregate metrics can be recomputed.

`tasks.md` divides implementation into five auditable stages. T48.1 builds the contract, T48.2
authors and freezes queries without retrieval, T48.3 records owner labels, T48.4 evaluates the
unchanged v2 retriever, and T48.5 closes QA. This ordering is intentional: combining authoring and
scoring in one task would let observed failures influence the supposedly held-out questions.

Decision D32 records the chosen composition, rejected alternatives, precommitted gates, 10x scale
impact, and most likely failure. The README, MVP brief, QA risk list, and a dedicated specification-
evidence document now state that T48 is only a draft contract—there is no new accuracy result.

### Source and method choices

Repository inspection found that the 2025 Fandom normalized rows explicitly declare
`staging_only_not_evaluation_or_canonical`. The T47 family projection also declares itself excluded
from evaluation ground truth. Reusing either as a convenient test dataset was rejected because it
would rewrite a frozen governance decision after the fact. Identity references may define what the
review question is, but scored query wording must be separately composed and human-approved.

Live marketplace scraping was also rejected for this first benchmark. It would introduce changing
results, unclear reuse rights, possible personal information, and irreproducible queries. Large
automatic typo generation was rejected because thousands of templated strings do not create
thousands of independent judgments. A smaller 105-case set is reviewable in Lite mode while still
covering every accepted, merged, and held family outcome.

The corpus feasibility check found 42 unique normalized family identities: 4 single-token, 15 two-
token, and 23 with at least three tokens. Haulerback, Crescendo, Bogzilla, and Draftnator are the
single-token cases. They must receive lexical challenges even though the current shared-token
eligibility rule may return nothing after a full-token misspelling. Exposing that weakness is the
reason for an independent evaluation; removing difficult cases would defeat it.

### Metrics, thresholds, and decision rationale

Recall@5 is the primary quality measure because this source presents bounded review suggestions,
not an automatic family decision. Recall@1 and MRR@5 still measure ranking usefulness. Family
coverage@5 prevents frequent/easy families from hiding families that never work, and metrics are
separated by query style. Merge controls must find their existing provisional-variant casting,
held identities must never appear as materialized review families, and unrelated zero-overlap
queries must remain empty.

The gates are frozen before data or results: Recall@5 at least 0.85, Recall@1 at least 0.65, MRR@5
at least 0.75, each query style Recall@5 at least 0.75, family coverage@5 at least 0.90, merge control
Recall@5 exactly 1.0, and zero held-family or unrelated-query violations. These thresholds decide
only whether PostgreSQL scale experimentation is justified. They do not authorize canonical or
production matching.

If v1 fails, the report must remain FAIL with raw cases and error categories. The team may use those
errors to design a new retriever, but the now-known v1 test cannot serve as final proof for that
replacement; a new v2 holdout is required. This costs additional authoring effort but avoids tuning
until a small benchmark says what the team wants to hear.

### Current impact, verification, and next step

This specification step changes no runtime code, model, index, data artifact, PostgreSQL state,
canonical behavior, or evaluation score. Static feasibility accounted for all 42 new families, 79
accepted release references, 4 merges / 9 references, and 7 holds / 12 references. The existing
184-test T47 baseline remains the executable starting point. A fresh rerun passed 184/184 in 1.637
seconds; static checks also confirmed all sixteen requirements are represented in task traceability,
all required design sections exist, and the repository diff has no whitespace errors. The known
non-failing Starlette legacy-`httpx` environment warning remains unchanged.

The next action is for the project owner to confirm the T48 requirements, design, and task order.
After confirmation, T48.1 can implement the strict benchmark builder and negative tests. T48.2 must
then freeze the query pack without running retrieval; results remain prohibited until all 105 labels
are separately approved in T48.3.

## 2026-09-11 — T47 closes with a requirement-by-requirement Lite QA verdict

### What was executed and what problem it solves

T47.4 verifies the entire family-level Human Knowledge RAG feature instead of treating the passing
implementation tests from T47.1–T47.3 as sufficient by themselves. The risk being addressed is a
false sense of completion: a family suggestion can look correct in the browser while its source
artifact is stale, a hold slipped into the index, the canonical decision changed, or documentation
quietly overstates exact-name retrieval as real-world accuracy.

The final QA therefore follows the feature from the original 100-row external pilot through review,
six owner-decision events, the stable family registry, the runtime projection, typed retrieval,
debug API/UI, and the independent canonical decision boundary. The result is PASS for T47's stated
Lite scope: family evidence is reproducible, typed, bounded, observable, safe to render, and unable
to become canonical identity. This pass does not promote any family or release variant and does not
approve PostgreSQL persistence or production retrieval quality.

### Code and documentation changes, affected areas, and reasons

No product code, runtime configuration, or data artifact needed modification in T47.4. Changing the
implementation during its closing QA would have mixed verification with another build step and
made the evidence harder to attribute. Instead, this task adds
`specs/family-level-human-knowledge/review.md`, which maps every FHK-R1–FHK-R16 requirement to a
specific test, artifact invariant, runtime observation, or repository diff result. The verdict is
worded as PASS for the debug-only integration boundary rather than an unrestricted product pass.

`docs/evidence/ai-evals/dual-rag-human-knowledge-v2.md` is added because the project rules require
AI/ranking outputs to have an explicit rubric record. It documents the 100-variant plus 42-family
corpus, the retrieval method, canonical isolation, API/UI safety, failure behavior, and the exact
limits of the available measurements. The central decision is to mark independent family
retrieval quality as `NOT EVALUATED`: the 42 smoke queries repeat the indexed approved names, so
using their 42/42 result as Recall or Top-1 accuracy would be leakage. The shared rubric now links
both the canonical scored evaluation and this separate v2 safety assessment.

The feature requirements, design, task list, main MVP brief, README, decision record, accumulated
evidence, and main QA review are updated from “final QA pending” to implemented and verified. These
changes give future reviewers one consistent state and make T48—not another T47 subtask—the clear
next dependency. Historical T47.1–T47.3 evidence remains intact so the sequence of decisions and
test-count growth can still be audited.

### Verification method and why it was selected

The QA uses three complementary evidence classes. First, executable tests exercise positive and
negative behavior: 184 unit, integration, API, evaluation, data, and UI tests passed. Second,
deterministic builders re-read the frozen artifacts and compare freshly constructed bytes, proving
the long external-data chain remains internally consistent. Third, a baseline diff compares the
implemented T47 feature with pre-T47 commit `785bb8d`, directly checking that prohibited canonical,
benchmark, calibration/policy, migration, and PostgreSQL implementation paths did not change.

This layered method was selected instead of relying only on the full test count. Tests demonstrate
behavior but do not automatically prove that a forbidden data file was untouched; a Git scope diff
does. Conversely, a clean diff cannot prove runtime behavior; service/API/UI tests do. The frozen
canonical evaluation supplies a third independent regression signal for the first RAG, while the
family smoke matrix tests only the second-RAG wiring.

Evaluation reports were generated in a temporary directory instead of overwriting checked-in
reports. T47 did not change the canonical benchmark or policy, so replacing historical report
artifacts merely because timing samples naturally vary would create noise and imply a new model
release. The fresh temporary report is used as QA evidence while the immutable catalog and
benchmark SHA-256 values remain the authoritative comparison.

### Detailed execution results

The fresh inventory contained exactly 100 provisional variants and 42 review families, totaling
142 documents with 142 unique IDs and UUIDs. Every approved brand/family exact query recovered its
expected document within Top-5; worst rank was 2. The existing BMW M3 GT2 result stayed a
`provisional_variant` at rank 1. Proton Saga appeared as a `review_family` debug candidate while the
canonical status remained `no_match` with null ID.

The complete suite passed 184/184 in 1.423 seconds. The deterministic chain passed fixture and
100-row pilot validation; pilot review; base queue; priority-one evidence and decision; five
research batches; five cumulative priority-two decision checkpoints; the 42-new / 4-merge / 7-hold
family registry; and the 42-document runtime projection. Python compilation, JavaScript syntax,
default and PostgreSQL-profile Compose parsing, and whitespace checks also passed.

The fresh 21-case synthetic canonical report preserved Recall@25 `1.0`, Top-1 `1.0`, hard-negative
accuracy `1.0`, precision `1.0`, false-match rate `0.0`, and coverage `0.8333`. Its direct-pipeline
p95 was `2.3898 ms`; warmed in-process HTTP/ASGI p95 was `2.675 ms`. These timings exclude Docker,
TCP, PostgreSQL, concurrent load, and production infrastructure and are recorded only as fixture
smoke evidence.

Diff inspection from `785bb8d` through the implemented T47 commit `d4fad68` found no change in
`data/catalog.json`, `data/benchmark.json`, calibration/policy artifacts or implementation,
migrations, or PostgreSQL implementation. The family projection retained SHA-256
`8615cbb99b453673599e1f9baf54f6900314d7ba64e53a31ea7891c71810b9d7`.

The first data-chain invocation stopped at its second command because that batch had not exported
`PYTHONPATH=src`, so the validator could not import the local package. This was an invocation error,
not a failed product assertion. The environment was corrected and the complete chain was restarted
from its beginning; every stage then passed. The only remaining suite message is the already known,
non-failing environment-wide Starlette legacy-`httpx` warning. Ruff and MyPy are unavailable in the
host environment, so neither is claimed as completed evidence.

### Remaining risk and next step

T47 is complete, but the second RAG's family accuracy remains deliberately unknown. Exact approved
names are useful for proving that all documents can be found; they do not tell us how misspellings,
seller abbreviations, extra release details, related casting names, or unseen noisy titles behave.
That is the most important unresolved risk because scaling a weak retrieval policy to PostgreSQL or
3,000 rows would make errors larger and harder to diagnose.

The recommended next task is T48: design and freeze an independently authored, casting-grouped
family holdout dataset, define metrics and error categories, and evaluate the current sparse /
`hashing-v1` / RRF second RAG without using the indexed names as its answers. T49 PostgreSQL and
pgvector measurement should proceed only after that quality result is understood; additional yearly
catalog ingestion follows those gates.

## 2026-09-11 — Family evidence becomes visible without being mistaken for a variant

### What was executed and what problem it solves

T47.3 completes the public debug boundary for Human Knowledge RAG v2. T47.2 already searched one
combined pool of 100 provisional variants and 42 review families, but the response model still
required variant-specific IDs. Its temporary serializer therefore hid family results to avoid
claiming that an accepted casting family was a reviewed release variant. That was safe, but it made
the new family retrieval impossible to inspect through the API and browser console.

The debug response can now carry both knowledge levels in their honest forms. Every item declares
either `knowledge_type=provisional_variant` or `knowledge_type=review_family`. A Proton Saga query
returns a family suggestion with its review-family identity, alias, and source references; it does
not receive casting/variant UUIDs that do not exist. The same request still ends as canonical
`no_match` with null canonical ID and UUID. The second RAG is therefore more observable without
gaining authority over the first/canonical RAG.

### Code changes, affected components, and reasons

`src/product_variant_resolver/schemas.py` replaces the single variant-only debug model with two
strict Pydantic models. A shared base contains only fields that genuinely apply to both document
types: review status, brand/casting display data, sparse/dense/RRF evidence, and matched tokens.
`HumanVariantKnowledgeCandidateDebug` adds casting and provisional-variant identities plus reviewed
label/example/case data. `ReviewFamilyKnowledgeCandidateDebug` instead adds review-family identity,
approved aliases, and source-record provenance. An annotated union uses `knowledge_type` as its
discriminator, so validation and generated OpenAPI describe the same two legal shapes. The debug
payload also gains `review_family_knowledge_version`, allowing a captured response to identify the
exact frozen family projection that produced it.

`src/product_variant_resolver/service.py` removes the T47.2 family filter. It first takes one slice
of the combined ranked candidates using `debug_candidate_limit`, then passes every candidate in
that slice to a type-aware converter. The converter constructs the matching strict model and raises
on any unsupported internal type. Slicing before conversion preserves one comparable ranking and
one bound across both sources; it avoids two lists that could each return the full limit. Explicit
construction also means no generic dictionary can quietly leak fields from one identity level into
the other.

`ui/index.html` renames the section to Human-knowledge candidates, adds a Type column, and states
that neither provisional variants nor review families can become the final answer. `ui/app.js`
branches only on the API discriminator. Variant rows retain their existing reviewed name and
series/variant text. Family rows use approved aliases and display `family only — variants
unreviewed`, making the missing variant a deliberate review state rather than an empty or fabricated
value. The catalog label now shows both the human catalog and family projection versions.

`tests/api/test_api.py` verifies both branches end to end. It checks family-only and variant-only
fields are absent from the opposite type, the family projection version is present only inside
debug, the combined list obeys a one-result limit, Proton Saga remains noncanonical, and OpenAPI
publishes the expected discriminator mapping. `tests/ui/test_debug_ui.py` supplies both candidate
types to the DOM harness and verifies their labels, family-only wording, version display, and table
shape. Markup-looking strings are placed in both a variant human label and family alias and remain
literal text.

### Technology and method choices, alternatives, and trade-offs

A discriminated union was selected instead of one large model containing many optional fields.
The optional approach would make contradictory payloads technically valid—for example a family
with a provisional-variant UUID, or a variant with only a family ID—and clients would have to infer
the intended shape from missing values. The discriminator gives FastAPI/OpenAPI clients one stable
switch and lets each branch keep its own required fields. A small inherited ranking base avoids
duplicating common evidence while still keeping identity fields separate.

The existing `human_knowledge_candidates` list and request limit were retained rather than adding a
second `review_family_candidates` list. Both document types already compete inside one RRF ranking;
splitting the response after ranking would obscure their relative position and could accidentally
double the amount of debug data. The trade-off is that a small limit may show only one type for a
particular query, which is the correct representation of the shared ranking rather than guaranteed
type quotas.

The UI continues to use DOM element creation and `textContent` rather than template strings or
`innerHTML`. Family aliases originate from externally researched data, so treating them as inert
text is a trust-boundary decision, not only a display preference. This approach is more verbose than
building an HTML string but makes markup-shaped data unable to create elements or event handlers.

### Decision and runtime impact

D31 is now implemented through projection, combined retrieval, and public debug presentation. The
change affects diagnostic output only. It does not change the 120-product canonical catalog,
canonical retrieval/ranking, calibration model, policy thresholds, confidence computation,
PostgreSQL schema/data, or evaluation ground truth. Family objects remain excluded from the final
identity path, and requests with `debug=false` still omit the entire debug object and all associated
knowledge/version metadata.

### Verification evidence

Seventeen focused API/UI tests passed in 0.277 seconds. Runtime assertions confirmed the two exact
response shapes, one shared result bound, generated OpenAPI mapping, family version metadata,
default omission, family/canonical isolation, existing variant behavior, loading/error states, and
text-safe rendering. The complete host suite passed 184/184. The suite's existing environment-wide
Starlette legacy-`httpx` deprecation warning remains non-failing and was not introduced by this
change.

### Incomplete work, risks, and next step

The implementation makes family suggestions inspectable; it does not prove they generalize to noisy
or unseen marketplace titles. The current 42-query result is exact-name self-retrieval against the
same family names used to build the index. Shared words can still retrieve unrelated families, so
it is not an accuracy claim and cannot justify canonical promotion, PostgreSQL rollout, or the
planned roughly 3,000-row expansion.

The next task is T47.4, the final Lite verification/documentation closure. It will rerun the entire
deterministic data chain and frozen canonical evaluation, map every FHK requirement to measured
evidence, close the feature review, and verify the repository diff remains within the Product
Variant Resolver folder. Only after that gate should T48 create an independently authored,
casting-grouped family retrieval evaluation.

## 2026-09-11 — Human Knowledge RAG v2 now searches 100 variants and 42 typed families

### What was executed and what problem it solves

T47.2 activates the frozen T47.1 family projection inside the second RAG. Before this change, the
Human Knowledge retriever understood only provisional variants and used their UUID field directly
as its index key. Passing a family through that shape would require a nonexistent variant ID and
would blur the boundary between an accepted casting family and an unreviewed release variant.

The runtime now loads 100 existing provisional-variant documents and 42 review-family documents as
two distinct internal types, then searches all 142 through one hybrid ranking pool. A family hit is
still review evidence only: the canonical retrievers, RRF, calibration, policy, confidence, and
response identity continue to operate exclusively on the 120-product canonical fixture catalog.
The `Hot Wheels Proton Saga` verification demonstrates the separation: the family is retrieved in
the human pool while the API remains `no_match` with null canonical UUID/ID and product.

### Code changes, affected components, and reasons

`src/product_variant_resolver/human_knowledge.py` now defines
`HumanVariantKnowledgeDocument` and `ReviewFamilyKnowledgeDocument`. Both expose common read-only
properties—`knowledge_type`, `knowledge_id`, `knowledge_uuid`, and `searchable_text`—without placing
family data into variant fields. The existing variant type retains casting and provisional-variant
IDs, series/variant labels, human names, pricing terms, initial names, and source cases. The family
type contains only its review identity, approved name/alias, and source-record provenance.

The same module adds a strict projection/manifest loader. It checks the exact schema/version,
projection checksum, allowed top-level/document/source fields, input references, 42/4/7 and
79/9/12 accounting, zero variant/canonical/PostgreSQL fields, debug-only eligibility, all exclusion
boundaries, source revision/license, UUIDv5 identity, deterministic order, alias policy, source-ID
format/uniqueness, and global knowledge ID/UUID uniqueness. The service cannot construct unless it
receives exactly 100 variant plus 42 family documents.

Sparse scoring, 192-dimensional `hashing-v1` dense scoring, and RRF now key both types by the common
knowledge UUID. This replaces every former direct reference to `provisional_variant_uuid` in the
index/ranking algorithm while leaving its formula and limit unchanged. The resulting index reports
`human-knowledge-hybrid-v2`.

`config.py`, `.env.example`, `Dockerfile`, and `docker-compose.yml` add explicit projection and
manifest paths. This makes local, environment-configured, and container startup follow the same
dependency contract instead of relying on an implicit current working directory.

`service.py` loads both frozen family files during construction and records bounded total, variant,
and family candidate counts on the existing human-retrieval trace span and privacy-safe completion
log. `api.py` exposes a `review_family_knowledge` readiness dependency with the projection version
and the explicit description `family-only review suggestions; never canonical identity`. Missing
or corrupt input prevents service construction, so health and resolve return 503 without identity.

The public `HumanKnowledgeCandidateDebug` model is intentionally unchanged in this task because it
requires provisional-variant fields. The transitional serializer therefore emits only variant
instances from the already bounded combined results. It does not coerce family IDs into variant
IDs, use null placeholders, or create a second unranked response list. T47.3 will replace this
temporary compatibility boundary with the specified discriminated union and safe UI rendering.

Tests now cover environment path selection, strict family loading, exact 100/42/142 counts, 142
unique IDs/UUIDs, all 42 exact family queries, searchable-field isolation, merge/hold absence, the
existing BMW regression, family/noncanonical service behavior, health versions, missing/corrupt
readiness, transitional debug safety, and privacy-safe per-type trace counts.

### Technology and method choices, alternatives, and trade-offs

Two frozen dataclasses plus a union were chosen over one large optional-field record. An optional
record could technically hold both types, but it would make invalid states—such as a family with a
variant ID or a variant without one—representable. The common properties give the ranking algorithm
the small interface it needs while each identity type keeps mandatory, meaningful fields.

The current deterministic sparse/hashing/RRF stack is reused rather than adding a neural embedding
model or a second family-only index. Reuse isolates the effect of the new data and preserves offline
operation. One shared pool also gives variant and family evidence comparable ranks under one limit;
separate indexes would need another fusion policy before their results could be meaningfully mixed.
The trade-off is changed human-pool document frequency and rank order, which is accepted only with
the BMW regression and 42-query smoke matrix and still requires independent T48 evaluation.

Loader validation is deliberately stricter than ordinary permissive JSON parsing. This artifact is
a trust boundary derived from external data, and silently accepting extra searchable fields or a
wider eligible-use list could connect held evidence to runtime. Future legitimate schema or alias
changes therefore require a visible version update. This increases upgrade work but makes accidental
scope expansion fail during readiness rather than silently changing search behavior.

The transitional family filter was chosen instead of implementing part of T47.3 inside this task.
Returning family objects through the current Pydantic model would either fail serialization or
fabricate variant fields. Filtering keeps the v2 internal integration testable and safe, but family
suggestions are not yet visible to API/UI users. That temporary limitation is explicit and removed
by the immediately following task.

### Decision and runtime impact

D31 is now implemented through its data-loading and retrieval layers. The second RAG has moved from
100 variant documents on v1 to a 142-document typed v2 index. The first/canonical RAG, canonical
catalog, final decision path, calibration artifacts, policy thresholds, PostgreSQL schemas/data,
and evaluation labels are unchanged. Family projection failure is now a required readiness failure
rather than a fallback to the older 100-document index.

### Verification evidence

Thirty-five focused tests passed in 0.635 seconds. The two existing UI harness tests also passed
after their model-version fixture moved to v2. The complete host suite passed 182/182 in 1.712
seconds. Runtime inspection found 100 variant documents, 42 family documents, 142 unique IDs and
UUIDs, 42/42 exact family queries within Top-5 with worst rank 2, and the BMW provisional variant at
rank 1. Proton Saga remained canonical `no_match` with null identity.

The canonical fixture evaluation remained Recall@25 `1.0`, Top-1 `1.0`, hard-negative accuracy
`1.0`, precision `1.0`, false-match rate `0.0`, and coverage `0.8333`. Python compilation,
projection/registry deterministic checks, fixture validation, Docker Compose configuration, and
whitespace checks passed. MyPy and Ruff were unavailable on this host, so neither is reported as a
passing gate. The only suite warning is the already documented machine-wide Starlette legacy-
`httpx` TestClient warning.

### Incomplete work, risks, and next step

The family candidates are now searched but remain intentionally hidden from the legacy debug
schema. This is safer than returning false variant fields, but it means v2 retrieval is not yet
fully observable through the public API or browser UI. Exact-name self-retrieval also remains only
a wiring smoke test; shared generic words can still surface unrelated families.

The next task is T47.3: add a Pydantic discriminated union, expose the family projection version in
debug responses, render variant and family candidates distinctly with text-safe DOM operations,
and prove default responses and markup-shaped external values remain safe. T47.4 then performs the
final Lite QA/evidence closure before T48 independent evaluation or any PostgreSQL/3,000-row work.

## 2026-09-11 — The accepted family layer becomes a frozen, debug-only knowledge projection

### What was executed and what problem it solves

T47.1 implements the first confirmed family-level second-RAG task. The T46 registry deliberately
mixes three review outcomes—42 new family identities, 4 links to existing human families, and 7
holds—and carries detailed decision and release evidence. Loading that audit object directly would
make held or variant-level material available to runtime code and would contradict the registry's
own `excluded_from=runtime_retrieval` boundary.

The new builder derives a separate 42-document knowledge projection. It accounts for all 53 family
decisions and all 100 Wiki release references before selecting only the 42 accepted creations. The
result retains 79 accepted source-record IDs as non-searchable provenance and creates zero
provisional variants, canonical promotions, and PostgreSQL rows. This gives T47.2 a small, explicit
runtime input without changing the running Dual-RAG system yet.

### Code and data changes, the affected parts, and why

`scripts/build_review_family_knowledge.py` is the new trust boundary between audit data and future
retrieval data. Its input validator checks the registry and manifest filenames, schemas, versions,
checksum, identity namespace, 42/4/7 family accounting, 79/9/12 row split, 100 unique release
references, and zero-promotion constraints. Every projected family must also keep its source-stable
UUIDv5, family-only identity level, accepted/unreviewed status, normalized family key, and explicit
`create_new_casting` decision with variants still held.

The builder does not copy whole registry entries. It constructs each document from an explicit
nine-field allowlist: type, family ID/UUID, identity level/status, brand, casting, aliases, and
source-record IDs. Only brand, casting, and aliases are declared future searchable fields. Release
objects, toy and collector numbers, series, variant notes, decision reasons, and evidence URLs are
therefore absent by construction rather than relying on later code to remember to ignore them.

`data/review_family_knowledge.json` contains the 42 sorted documents. Its companion manifest freezes
both T46 input hashes, the projection hash, allowed document/search fields, permitted debug-only
use, forbidden canonical/evaluation/PostgreSQL uses, 42/4/7 family counts, 79/9/12 row counts, and
the original 100-row source total. Because the projection is a generated artifact, it contains no
build timestamp; the same inputs reproduce identical bytes.

`tests/test_review_family_knowledge_projection.py` adds six tests around the trust boundary. The
positive cases verify exact selection, unique IDs/UUIDs, the field allowlist, all 79 accepted source
references, frozen checksums, and byte reproduction. Negative cases mutate checksums, family count,
UUID, aliases, eligibility, exclusions, and output freshness. The overwrite test preloads known-good
files and proves both an invalid build and a failed `--check` leave those bytes untouched.

### Technology and method choices, alternatives, and trade-offs

The implementation uses the Python standard library rather than adding a data-build dependency.
`json.dumps(..., sort_keys=True)` plus sorted documents/aliases/source IDs provides deterministic
serialization; SHA-256 connects each output to exact inputs; UUIDv5 validation confirms identity is
derived from the immutable review ID rather than editable display text. T46 v1 permits exactly the
display name as its sole alias; accepting an added alias under the same version would silently widen
retrieval language, so the builder rejects it and requires a future reviewed version change.
Temporary files are fully written and `fsync`ed before `os.replace`, so validation failures never
truncate accepted outputs.

An alternative was to put a `searchable_text` string inside every document. That would duplicate
normalization policy and could let a future builder accidentally append evidence or release fields.
The projection instead freezes the three searchable source fields and leaves text construction to
the strict loader planned for T47.2. Another alternative was to copy the T46 registry and filter it
at query time; that would enlarge the trusted runtime surface and make a forgotten filter capable
of indexing holds. The smaller allowlisted projection makes the safe state observable in the data
itself.

Atomic replacement is performed per output file rather than through a database transaction. That
is appropriate for two checked-in local artifacts because the manifest checksum detects any
interrupted or mixed pair at the next `--check`/load. T47.2 will fail readiness on such a mismatch.
No PostgreSQL write is used here because persistence would combine an identity-boundary change with
an unevaluated retrieval and scaling decision.

### Decision and runtime impact

D31 moves from proposal to partial implementation: the separate projection is now real and frozen,
but the proposed 142-document index is not. Configuration, service construction, human-knowledge
models, API schemas, health output, UI, canonical ranking, confidence, calibration, and database
contents are unchanged. The currently running second RAG therefore still contains only the 100
human-backed provisional variants and still reports its v1 index.

### Verification evidence

The builder produced exactly 42 documents and its non-mutating check reproduced both outputs. Six
focused tests passed in 0.150 seconds. Python compilation, the T46 registry check, the fixture
validator, and a 100-character source-line check passed. The complete host suite passed 174/174 in
1.612 seconds. It emitted only the already documented non-failing Starlette legacy-`httpx`
TestClient warning; this task changes no web dependency. Ruff was unavailable in the host
environment, so no Ruff result is claimed.

### Incomplete work, risks, and next step

The projection is deliberately dormant. Until T47.2 adds strict loading and manifest validation,
these 42 documents do not participate in retrieval and cannot appear in debug output. The 79 source
references establish provenance but do not prove any release variant. The earlier exact-name
simulation is still a wiring smoke result rather than independent search-quality evidence.

The next task is T47.2: add settings, typed variant/family document models, strict projection
readiness, and one combined 142-document sparse/hashing-dense/RRF index while proving that all human
candidates remain outside canonical identity and confidence. API/UI discrimination stays in T47.3;
independent retrieval quality remains T48, before PostgreSQL or the roughly 3,000-row expansion.

## 2026-09-11 — Family-level second-RAG integration is specified as a typed projection

### What was executed and what problem it solves

T47 analyzes how the 42 stable T46 review-family identities can become useful search suggestions
without being mislabeled as variants or allowed to affect canonical answers. The current second RAG
contains 100 human-confirmed provisional-variant documents; every internal document and debug item
requires a provisional variant ID. Reusing that shape for family-only knowledge would reintroduce
the exact fabricated-variant problem T46 avoided.

The new Lite specification defines a separate family-knowledge runtime projection plus a typed v2
human-knowledge index. The projection selects only 42 accepted new families. Four merge links do not
become new documents because their existing human-backed families are already searchable; seven
holds and all held release details remain outside the index. This resolves the schema and ingestion
design question while preserving current runtime until the owner confirms implementation.

### Code and documentation changes and why they were made

`specs/family-level-human-knowledge/requirements.md` adds sixteen EARS requirements covering a
deterministic runtime projection, exact selection, searchable-field allowlisting, typed documents,
unified retrieval, exact-name smoke and existing-variant regression, hold/merge behavior, canonical
isolation, debug API/UI, readiness, observability, persistence/evaluation limits, and reproducibility.

`design.md` maps those requirements to the current implementation. It identifies affected settings,
loader/retriever, service, API health, Pydantic schemas, UI, and tests. It defines
`pvr-review-family-knowledge-v1`, the `provisional_variant` / `review_family` discriminated debug
union, a single 142-document sparse/dense/RRF pool, projection/version fields, fail-closed startup,
safe UI rendering, and the absence of any edge from human candidates to canonical policy.

`tasks.md` separates the future build into four bounded units: projection generation, typed v2
retrieval/readiness, debug API/UI integration, and QA/documentation. Every FHK requirement is mapped
to at least one implementation or verification task. The main MVP brief, QA review, README,
decision register, and T47 spec evidence now link the same proposed boundary.

### Technical choices, alternatives, and trade-offs

The T46 registry will not be loaded directly. It is an audit artifact that intentionally contains
hold explanations and held release provenance and declares itself excluded from runtime retrieval.
Rewriting that artifact would invalidate its frozen evidence; loading it would risk making
non-searchable fields available to future code. A small allowlisted projection creates a new,
explicitly authorized runtime contract while leaving adjudication history immutable.

The two document types will share one human-knowledge index and one result limit. A separate family
retriever/list would minimize changes to the existing variant schema, but callers could not compare
its ranks with variant ranks and the UI would need two competing second-RAG sections. A discriminated
union retains type-correct fields while one sparse/dense/RRF pool provides deterministic ordering.

Family searchable text is restricted to brand, approved name, and aliases. Source record IDs remain
available as bounded debug provenance but do not affect scoring. Series, toy numbers, variant notes,
decision reasons, evidence URLs, and held names are excluded because none was approved as family-
level search language.

The current hashing-v1 embedding and RRF algorithm are retained instead of selecting a neural model
or new ranker. The purpose of T47 is safe wiring, and the existing deterministic method makes change
effects traceable. A new model would mix identity integration with an unmeasured algorithm change;
T48 exists to determine whether stronger retrieval is actually needed.

### Decision changes

No family, variant, canonical, or database decision changes. The new architectural proposal derives
a 42-document runtime projection from T46 rather than making the T46 registry itself runtime data.
The projected families and existing variants become typed peers inside the second RAG, but remain
debug-only and completely outside canonical confidence and identity.

T47 is complete only as a proposed specification. Runtime implementation, API/UI changes, and data
projection generation remain blocked by the Lite G1* confirmation step.

### Verification evidence

A read-only simulation used the current `HashingEmbedding`, sparse scoring, and RRF formulas over the
100 existing human variant documents plus the proposed 42 family documents. All 142 UUIDs were
unique. All 42 exact `Hot Wheels + family name` queries recovered the intended family within Top-5;
the worst rank was 2. The existing BMW M3 GT2 Neon Speeders provisional variant remained rank 1,
and the `'67 Chevy C10` merge query continued to return its existing variant without a duplicate
family document.

The same simulation showed the most important unresolved risk: `Power Wheels Dune Racer` did not
return a held Power Wheels identity—none exists—but shared `racer` language could return another
accepted family. This is not a contract violation, yet it demonstrates why self-retrieval cannot be
reported as quality. T48 must measure false and useful suggestions on independently written queries.

No product code or data changed. A fresh complete host run passed 168/168 tests in 1.628 seconds.
It emitted only the already documented Starlette legacy-`httpx` TestClient deprecation warning;
the warning is unrelated to this documentation-only change and remains non-failing. Documentation
structure, 16/16 requirement traceability, whitespace, and repository scope were also verified
before commit.

### Incomplete work, risks, and next step

The runtime projection, v2 typed loader, discriminated debug models, readiness dependency, and UI
rendering do not yet exist. Adding 42 documents will change human-source document frequencies and
may reorder debug suggestions even though canonical output remains isolated. Exact-name success on
the source labels is not evidence for noisy marketplace text.

After the project owner confirms requirements, design, and tasks, the next immediate step is T47.1:
build and freeze the 42-document family-knowledge projection. T47.2–T47.4 then integrate, render,
test, and document v2. T48 independently evaluates retrieval before T49 PostgreSQL work or expansion
toward roughly 3,000 reviewable rows.

## 2026-09-09 — Accepted family decisions become stable review entities without fake variants

### What was executed and what problem it solves

T46 implements the owner-confirmed family-materialization contract. Before this step, the 42
accepted `create_new_casting` outcomes existed only inside a long adjudication queue; they had
decisions and evidence but no standalone, database-compatible review identity. The new registry
makes those family concepts directly inspectable and reproducible without claiming that any of the
100 associated Wiki releases has been reviewed as a variant.

The generated result contains 42 new family entities over 79 source rows, 4 links to existing
human-backed families over 9 rows, and 7 explicit hold exclusions over 12 rows. Every source row is
represented exactly once and remains `held_for_variant_review`. The registry therefore closes the
family-identity materialization gap while keeping the release-level backlog visible.

### Code changes and why they were made

`build_review_family_registry.py` verifies six inputs before building: the final adjudicated queue,
its manifest, the normalized 100-row staging dataset, its source manifest, the 97-family human-
backed catalog, and its manifest. It checks filenames, versions, SHA-256 values, queue completion,
source revision/license, family/row accounting, decision vocabulary/scope, promotion hold, exact
staging-row equality, and existing human-family identities. This prevents a stale or hand-edited
input from quietly becoming a new identity registry.

For each accepted creation, the builder reuses `family_review_id` as the public review ID and derives
a UUIDv5 from the fixed `product-variant-resolver:review-family:fandom-hot-wheels-wiki` namespace.
For each accepted merge, it resolves the exact existing human `casting_id` and `casting_uuid` and
does not mint another UUID. Holds retain names, reasons, evidence, and release references with
`retrieval_eligible=false`.

The builder emits `data/review_family_registry.json`, a checksum/count manifest, and a readable
Markdown report. JSON serialization and list order are deterministic and have no build timestamp.
Write mode fully validates and prepares all content before replacing outputs; `--check` builds
expected content in memory and compares all three files without writing.

`test_review_family_registry.py` adds nine tests. They verify exact 42/4/7 family and 79/9/12 row
splits, unique UUIDv5 values, one approved alias per new family, exact merge targets, all seven named
holds, 100 unique held releases, complete decision/source provenance, frozen hashes, deterministic
reproduction, and non-mutating check mode. Mutated checksum, partial queue, widened variant scope,
duplicate source row, missing merge target, and collision with an existing human family all fail.

`validate_fixture_data.py` now treats the registry and manifest as part of project-wide integrity.
It repeats the high-value checksum, counts, UUID, alias, merge-target, hold, source provenance, row
coverage, and zero-promotion/index/persistence checks so routine validation cannot ignore the new
artifact.

### Technical choices, alternatives, and trade-offs

UUIDv5 was selected instead of random UUIDv4 because identical reviewed input must yield identical
identities on every machine. The UUID input excludes display name and registry version: punctuation
or a future label correction can change presentation without replacing identity, while a genuinely
different source family keeps a different immutable review ID.

The registry keeps full release references—including year, toy/collector number, series position,
and variant note—but none becomes an alias or variant object. Discarding them would lose the path to
later release review; indexing them now would make unverified release details influence search.
Keeping them as held provenance supports future work without weakening today's claim.

All seven holds appear in the registry as exclusions rather than being omitted. Omission would make
the 100-row accounting incomplete and allow a future importer to rediscover the same unsafe names.
Conversely, an exclusion cannot be indexed. Power Wheels Dune Racer therefore remains visible as a
renamed-lineage problem without silently becoming a Bogzilla alias.

The outputs are prepared in temporary sibling files and then replaced after validation. This is
safer than writing each artifact incrementally and meets the invalid-input preservation goal. It is
not described as a multi-file database transaction: an operating-system or power failure between
final replacements remains a recoverable stale-output condition detected by `--check`.

Runtime integration remains deliberately separate. Extending the existing variant-based
`HumanKnowledgeDocument` now would combine data materialization with API/debug schema and ranking
changes. T46 gives that future work a stable, validated input while keeping the currently proven
Dual-RAG path unchanged.

### Decision changes

The T45 proposal is now owner-confirmed and implemented. The 42 accepted families change from
decision-layer concepts to stable review-family entities; the 4 merges become explicit links. This
does not change their family decisions, and the 7 holds remain non-materialized exclusions.

No release changes from hold to accepted. No canonical or existing human-backed runtime identity is
rewritten. Provisional-variant creation, canonical promotion, runtime indexing, and PostgreSQL row
creation all remain exactly zero.

### Verification evidence

The focused registry suite passed 9/9. The complete host suite passed 168/168 in 1.500 seconds on
Python 3.14.6; only the already documented legacy-`httpx` TestClient warning appeared. The project
fixture and Wiki pilot validators, review/base queue/priority-one chain, all five research batches,
all five priority-two decision checkpoints, registry `--check`, Python compilation, default and
PostgreSQL Compose configurations, and whitespace check all passed.

Registry SHA-256 is
`3f289b802cc2e8280ed5c3586d87cfabbee7ce37b10ae79504b5aa6b8837367d`; manifest SHA-256 is
`ae9eda741aa2ec7cb9354424e17b789ba73c05890859e73d19cd845c5cab3ff2`; readable report SHA-256 is
`5312f2b86b3209c815def09417628a0248a8e50251f88ec3a48aeb7ed03203b5`. The combined fixture
checksum including the registry is
`2c72ca83a74e090d8e89e6df124fb1520355643fd8629f71535f099269d45972`.

### Incomplete work, risks, and next step

The family registry is not loaded by `src/product_variant_resolver`; it does not alter current
Dual-RAG candidates, API responses, health state, or PostgreSQL. The 100 release references still
need separate variant review, and the seven held family names still need tool- or lineage-qualified
decisions. Text-source evidence may contain upstream inaccuracies.

The next immediate task is T47 specification: define a distinct family-level human-knowledge
document, its debug fields, ranking inputs, hold exclusion, readiness checks, and the invariant that
a family suggestion can never populate canonical identity. Only after implementation and an
independent casting-grouped holdout evaluation should this registry be considered for PostgreSQL or
the expansion toward roughly 3,000 reviewable rows.

## 2026-09-09 — Family materialization is specified without inventing variants

### What was executed and what problem it solves

T45 turns the post-adjudication question—“how do 42 accepted family decisions become usable
entities?”—into a Lite specification that can be tested before data is changed. The final queue has
complete family decisions, but its 100 release rows still lack variant-level approval. The new
requirements, design, and task plan make that distinction executable instead of leaving the next
developer to infer it from prior reports.

The specification accounts for the complete queue: 42 accepted new-family outcomes covering 79
source rows, 4 accepted merges covering 9 rows, and 7 holds covering 12 rows. A read-only comparison
against the 97 existing human-backed families found no exact normalized collision for the 42 new
names, and the proposed readable labels do not collide with each other. These checks support the
current packet but are not used as the permanent identity mechanism.

### Code and documentation changes and why they were made

`specs/review-family-materialization/requirements.md` adds thirteen EARS-style requirements. They
cover frozen input verification, the closed decision vocabulary, stable family identities, merge
links, hold exclusion, conservative aliases, complete provenance, deterministic output, exact
accounting, fail-closed validation, runtime/database boundaries, and a non-mutating check mode.

`design.md` defines a separate `pvr-review-family-registry-v1` with three sections: 42 new entities,
4 merge links, and 7 hold exclusions. Accepted source releases are stored only as
`held_release_references`; the schema intentionally has no `provisional_variants` field. It also
defines CLI inputs/outputs, UUIDv5 identity, manifest fields, a ten-stage build algorithm, atomic
write behavior, security constraints, and test coverage.

`tasks.md` breaks the next implementation milestone into builder/artifact work, fail-closed
validation/tests, and QA/documentation. The main MVP brief marks T45 complete only as a proposed
specification and leaves T46 implementation pending owner confirmation. The QA review, decision
register, and this log now point to the same boundary and measured 42/4/7, 79/9/12 totals.

### Technical choices, alternatives, and trade-offs

The key choice is a separate family registry rather than adding rows directly to
`human_backed_catalog.json`. The existing catalog contains 97 castings and requires each one to have
at least one human-confirmed provisional variant. Creating an `unclassified` placeholder for each
Wiki family would be convenient for the current loader, but it would fabricate 42 variants and make
family approval look like release approval. Allowing empty variant arrays would weaken an existing
fail-closed invariant and still leave runtime document semantics unclear.

The immutable `family_review_id` is reused as the public review ID. A UUIDv5 derived from a fixed
project/source namespace plus that ID provides a database-compatible key. Display names and slugs
are excluded from identity derivation because names may later need punctuation corrections or tool-
qualified disambiguation; using them would either change identity after correction or collide as
the dataset grows.

The four merges do not receive new UUIDs. They link to the already frozen human catalog family,
which avoids duplicating one casting under a second source-specific identity. The seven holds remain
visible as audit exclusions but cannot be indexed. In particular, Power Wheels Dune Racer is not
silently added as a Bogzilla alias because the owner authorized a hold, not a merge.

The specification stops before Dual-RAG and PostgreSQL. Bundling those changes could make progress
appear faster, but it would combine data identity, API/debug semantics, retrieval quality, schema
migration, and scale testing in one difficult-to-audit change. The Lite sequence keeps each question
small: establish stable review entities first, then design family-level retrieval, evaluate it, and
only afterward persist/scale it.

### Decision changes

No T44 family decision changes. The new decision is architectural: accepted family-only outcomes
will be materialized in a dedicated review registry, not as fake provisional variants or immediate
PostgreSQL products. The 42 creates remain accepted, the 4 merges retain their existing targets, the
7 holds remain excluded, and all 100 release references remain held.

T45 is complete as a specification proposal, not as implementation approval. The project owner must
confirm the three spec documents before T46 begins, as required by the Lite spec gate.

### Verification evidence

Static inspection verified the current queue is `adjudicated` with 53 completed and zero pending
families. Recomputed partition counts are 42 create, 4 merge, and 7 hold; source-row totals are 79,
9, and 12 respectively and sum to 100. The 42 proposed creations have zero exact normalized
brand/casting collisions with the 97 existing human-backed families and zero collision under the
current readable-ID form.

No product code or data artifact changed. A fresh complete host rerun still passed 159/159 in 1.418
seconds; the machine-wide Python 3.14 interpreter emitted only the already documented legacy-`httpx`
TestClient warning. Documentation whitespace and repository-scope checks passed. An explicit
traceability table maps all thirteen RFM requirements to implementation and verification tasks and
records deferred Dual-RAG, evaluation, PostgreSQL, and approximately 3,000-row work.

### Incomplete work, risks, and next step

The specification has not yet been confirmed by the project owner, and
`build_review_family_registry.py` does not exist. UUID namespace spelling, output filenames, and
the family/merge/hold model become implementation contracts only after confirmation. External text
sources may still contain errors, and a family-level identity remains weaker than a physically
verified release variant.

After confirmation, the next immediate task is T46.1: implement the deterministic registry builder
and generate its three checksum-frozen artifacts. T46.2 will add fail-closed tests and validation;
T46.3 will run QA and document measured results. Runtime Dual-RAG integration remains T47 rather
than being assumed by registry creation.

## 2026-09-09 — Final owner decisions close family review while all variants remain held

### What was executed and what problem it solves

T44 converts the project owner's request to proceed into a durable decision record for the exact
final T43 packet. The packet was already bounded to nine families and disclosed as six machine
creation recommendations plus three evidence-based holds. Storing the response in the repository
solves two problems: the decision no longer depends on transient conversation history, and the
system can distinguish a human-authorized family outcome from the preceding machine research.

The accepted creation outcomes are Proton Saga, Small Bloc, Super Twin Mill, The Vanster, Twin Mill
Gen-E, and X-34 Landspeeder. Nissan Skyline GT-R (BNR32), Power Wheels Dune Racer, and Standard Kart
remain held. The cumulative queue is now closed at family scope: all 53 families have outcomes,
including 4 existing-family merges, 42 accepted new-family decisions, and 7 holds. This resolves
the current 100-row pilot's family-review backlog without pretending that its release variants are
ready for production.

### Code changes and why they were made

`priority-2-batch-05-decisions.json` is the human authority layer. It copies the exact frozen T43
recommendations, names the project owner as decision maker, timestamps the decision, retains every
source reference, and explicitly limits scope to family decisions. Decision data stays separate
from both machine research and generated output so that provenance can be inspected and invalid
input can be rejected instead of silently rewriting history.

`apply_fandom_priority_two_decisions.py` now routes `--batch 5` from the batch-04 cumulative queue
through a new versioned result. The generic result-status rule reports `adjudicated` only when no
family remains pending; earlier checkpoints continue to report `partially_adjudicated`. The
readable result adds the final six accepted family names, the three retained holds and their
reasons, and the explicit statement that the 53-family queue is complete while release variants
remain held.

The generated cumulative queue, manifest, and Markdown result are checked in as reproducible build
artifacts. `test_fandom_priority_two_decisions_batch_five.py` adds six tests for the exact nine-
family packet, exact six-create/three-hold split, 13 current release rows, all 53 accumulated
decisions, six ordered history events, family-only scope, 100 held variants, zero promotion,
frozen hashes, and deterministic regeneration. It also supplies altered, incomplete, duplicate,
and widened decision inputs and requires each to fail closed.

README, the external-data guide, MVP task brief, QA review, decision register, and T44 evidence now
use the same totals and boundary wording. This avoids a future maintainer reading “53 completed” as
“53 records inserted into PostgreSQL” or “42 new searchable products.”

### Technical choices, alternatives, and trade-offs

The final status is derived from the count of pending decisions rather than hard-coded to batch 5.
That makes the state describe the data: batches 1–4 remain partial, while any valid future terminal
queue can become adjudicated for the same reason. It avoids special-case business logic tied only
to a filename, while preserving byte-for-byte reproduction of earlier artifacts.

The three holds are accepted as completed decisions instead of being left pending. “Hold” means the
owner has decided that current evidence is insufficient or points to a conflicting identity; it is
not unfinished paperwork. BNR32 still spans a separate same-scale RLC tool, Standard Kart still
spans character-bearing and driverless tools on one page, and Power Wheels remains a renamed
Bogzilla release for which an automatic new family or silent merge would both exceed the evidence.

The six accepted creations are not written directly into `human_backed_catalog.json`, the canonical
fixture, or PostgreSQL. Immediate insertion would be faster, but it would require unmade decisions
about deterministic IDs, aliases, renamed lineages, provenance, and how family approval relates to
individual year/color/toy-number variants. A separate stable review-family contract is the smaller
and safer next design step, especially before scaling toward roughly 3,000 rows.

### Decision changes

The six T43 creation recommendations change from pending machine proposals to completed,
project-owner-attributed `create_new_casting` decisions. The three T43 proposed holds likewise
become completed owner holds without changing their evidence or reasons. No earlier family outcome
is modified; all five earlier owner batches are preserved and the new batch is appended as history
event six.

The resulting totals change from 44 completed / 9 pending to 53 completed / 0 pending. Accepted
new-family decisions increase from 36 to 42 and completed holds increase from 4 to 7; accepted
existing-family merges remain 4. Held release rows increase from 87 to all 100 because the thirteen
rows in the final packet now belong to completed family decisions but still have no variant-level
authorization. Promotion remains zero.

### Verification evidence

The focused T44 module passed 6/6. The complete host suite passed 159/159 in 1.440 seconds on Python
3.14.6. All five research packets and all five priority-two cumulative decision checkpoints
reproduce; the decision checkpoints report completed/pending totals of 14/39, 24/29, 34/19, 44/9,
and 53/0. Fixture/pilot validation, base review/queue/priority-one checks, Python compilation,
default and PostgreSQL Compose configuration, and `git diff --check` also passed.

The decision file checksum is
`a5dc269b2ced7b8423fd0cf321ab470922c12b7520c88944f99539cbdad2626b`; the final cumulative queue is
`989bc914f9493051a071472c9defd352fe1cb8cc217c062e1f479bdcb9c6e4d8`; the readable result is
`245ded3d564a94eccc017a942189eb38a40f4c5a08652d724be3dc759e2ddb10`; and the manifest is
`6b532978c86adf39dbc2f41222d41ca9b765b1c615dce5453a0ba04955a9f6ff`. The known machine-wide
Python 3.14 legacy-`httpx` TestClient warning remains documented; the constrained Python 3.12
container path was previously verified with `httpx2`.

### Incomplete work, risks, and next step

Family adjudication is complete, but materialization and release-variant adjudication are not. The
42 accepted new-family outcomes do not yet have stable review IDs and are not Dual-RAG candidates;
the 7 holds still require tool-qualified or lineage-specific resolution before they can enter that
source. None of the 100 Wiki rows is canonical or promotion-eligible.

The next immediate step is to write a Lite specification for the stable review-family
materialization contract. It should define deterministic IDs, aliases, provenance, lineage links,
hold exclusion, idempotent generation, and the boundary between family acceptance and later
release-variant review. Only after that contract is accepted should implementation update the
human-backed retrieval source or PostgreSQL, and only then should yearly-list expansion continue
toward roughly 3,000 reviewable rows.

## 2026-09-09 — Final priority-two research preserves renamed and multi-tool identity boundaries

### What was executed and what problem it solves

T43 verifies the exact T42 cumulative checkpoint and selects all nine remaining pending priority-2
families in their existing queue order. Earlier research batches assumed ten-item slices; this one
uses the true remainder rather than duplicating a family, skipping a family, or padding the work
with a record outside the current 100-row pilot.

The packet covers thirteen Wiki release rows across Nissan Skyline GT-R (BNR32), Power Wheels Dune
Racer, Proton Saga, Small Bloc, Standard Kart, Super Twin Mill, The Vanster, Twin Mill Gen-E, and
X-34 Landspeeder. Six names have a dedicated single-casting page plus non-Fandom exact-name
corroboration and receive machine `create_new_casting` recommendations. Three remain held because
their text names do not identify one safe physical lineage.

### Code changes and why they were made

`priority-2-batch-05-source-notes.json` freezes the nine-family research input. Each entry retains
the queue ID and display name, a concise Wiki observation, and at least one observation from a
separate publisher. The independent sources are Hot Wheels Collectors News Catalog, All Hot
Wheels, Wheel's Garage, and Hot Wheels Collectors. Only source URLs and paraphrased text claims are
stored; no images or external page copies are added to the repository.

`build_fandom_priority_two_research.py` now accepts `--batch 5`, reads the batch-04 adjudicated
queue and manifest, and passes an explicit `batch_size=9`. The builder still defaults to ten for
batches 01–04. Its selection metadata is generated from the actual bounded size, so the artifact
states exactly what was selected rather than preserving an inaccurate “first 10” label.

The source-page vocabulary adds `renamed_existing_casting` and `multi_casting_page`. A renamed
release is held because its marketing/display name points back to an existing casting lineage; a
multi-casting page is held because one page contains more than one tool under the same display
name. These are distinct from a formal `disambiguation` page and from `homonymous_castings`, where
a separate page exposes the conflict. Each class has its own fail-closed recommendation reason.

The initial implementation briefly reused the new multi-tool wording for the legacy
`disambiguation` branch. The cross-batch `--check` immediately detected that batch 01 would no
longer reproduce byte for byte. The branches were separated, restoring the original text for old
batches while keeping the new classification for batch 05. No checked-in prior artifact was
rewritten.

`test_fandom_priority_two_research_batch_five.py` adds six tests. They require the exact final nine
families and thirteen rows, the six-create/three-hold split, the named hold set, Bogzilla lineage
for Power Wheels, both Standard Kart tool numbers, the distinct Nissan RLC tool, two-host evidence
for every creation, preserved related-lineage context, pending reviewer fields, variant hold, zero
promotion, hashes, and deterministic regeneration.

### Technical choices, alternatives, and trade-offs

Power Wheels Dune Racer is not treated as a new casting. HYX52 appears on the Bogzilla page as a
release named Power Wheels Dune Racer, and an independent listing pairs both names. Automatically
creating a Power Wheels family would duplicate the FJV61 physical lineage; silently merging it to
Bogzilla would also exceed a machine research step. A named `renamed_existing_casting` hold keeps
the likely relationship visible for the owner and later entity design.

Standard Kart is not treated as one family merely because both tools share one page. The evidence
separates a character-bearing 2019 GBG26 tool from the driverless mainline GRX17 tool whose 2025
release is HYW83. The current toy number identifies the latter release, but a name-keyed family
would remain ambiguous. `multi_casting_page` records the evidence shape without pretending the page
is a formal disambiguation index.

Nissan Skyline GT-R (BNR32) is held because the main page maps HYY72 to the Jun Imai lineage while
a separate 2026 RLC page documents a completely different opening-hood JJY54 tool at the same 1:64
scale. The RLC qualifier provides useful context, but the base display name remains shared. This is
stricter than the earlier Mercedes XL case, where the separate page was explicitly an upscaled
1:43 product rather than a competing same-scale tool.

The other six names remain separate when their relationship is expressed through a different
name, a documented continuous retool, or a distinct product line. The Vanster retools stay in one
page lineage; Twin Mill Gen-E and Super Twin Mill retain names distinct from the original Twin Mill;
the wheeled X-34 Landspeeder remains distinct from the differently named Starships product. This
avoids both over-splitting every tooling change and over-merging all related designs.

### Decision changes

No project-owner decision changed. All nine T43 records remain pending machine research. Proton
Saga, Small Bloc, Super Twin Mill, The Vanster, Twin Mill Gen-E, and X-34 Landspeeder receive
creation recommendations. Nissan Skyline GT-R (BNR32), Power Wheels Dune Racer, and Standard Kart
receive proposed holds.

The T42 cumulative queue therefore still reports forty-four completed and nine pending family
decisions, including four merges, thirty-six accepted new-family decisions, and four completed
holds. Eighty-seven release rows under completed family decisions remain variant-held. The thirteen
current research rows are also held. No stable ID, catalog object, PostgreSQL row, Dual-RAG result,
calibration input, evaluation label, or promotion status changed.

### Verification evidence

The focused T43 module passed 6/6. The complete host suite passed 153/153 in 1.418 seconds on Python
3.14.6. All five research batches reproduce byte for byte; the first four remain unchanged after
adding the bounded final-size and evidence-class support. The known legacy-`httpx` Starlette
TestClient warning remains limited to the machine-wide environment, while the constrained Python
3.12 runtime was previously verified with `httpx2`.

The source-note checksum is
`f230b8c5ec5f6bd5b7569659ab23925f2c6d56c6e7e689df1de2067da5c6ca13`; research JSON is
`a49ad2f32f255f800d32ab5466640e2b8138b6ff743e601f58d74feee622626a`; the readable report is
`d782096f9dd2c3959e5d9321ce16fdcbb906ff2d2c2cf228cd4c34934254454f`; and the manifest is
`03a180d7e7ec919b6a9f880a12a05bf77287d233dd1a37d77a63fb22af972426`. Final data-chain,
compilation, Compose, and whitespace checks are recorded in the T43 evidence and QA review.

### Incomplete work, risks, and next step

The research sources can change, collector catalogs may inherit upstream mistakes, and text claims
do not replace physical-tool verification. None of the six creation recommendations is an owner
decision. The three holds need an explicit choice about tool-qualified IDs, aliases, or target
lineages before materialization.

The next immediate task is T44: present the exact six-create/three-hold packet to the project owner
and, only after authorization, append the final priority-2 decision batch. That will close the
current 53-family adjudication queue at family scope while every release variant remains held. A
new specification must then design stable review entities and the expansion path toward roughly
3,000 reviewable variants without inserting provisional research directly into production data.

## 2026-09-09 — Batch-04 research becomes an attributable eight-create/two-hold decision layer

### What was executed and what problem it solves

T42 converts the project owner's bounded follow-up authorization into a repository-owned decision
record. The immediately preceding T41 handoff identified the exact eight creation recommendations,
the two held names, why those names remain ambiguous, and that every release variant would stay
held. Recording the response separately prevents the system from confusing a machine research
recommendation with a human decision or relying on transient conversation history.

The eight accepted review-layer families are Lamborghini Huracán Sterrato, Max Steel, Mazda
Autozam, Mazda REPU, Mercedes-Benz 500 E, Monster High Ghoul Mobile, Morgan Super 3, and Nerve
Hammer. Mazda MX-5 Miata and Nissan Skyline 2000GT-R LBWK remain held. The cumulative queue moves
from thirty-four completed / nineteen pending families to forty-four completed / nine pending,
while all twenty-three rows in the current batch remain variant-held.

### Code changes and why they were made

`priority-2-batch-04-decisions.json` is the new immutable authorization input. It records
`project_owner`, an ISO-8601 UTC decision time, conversational provenance, and one decision for each
T41 packet. Each entry uses `casting_family_only`, keeps `target_family_id` null, gives a written
family-specific reason, references the frozen research packet and supporting sources, and sets
`variant_decision` to `hold`. Keeping the decision input separate from both research and output
makes the actor, time, scope, and evidence independently inspectable.

`apply_fandom_priority_two_decisions.py` now accepts `--batch 4`. The new mapping reads the T40
cumulative queue, T41 research, and T42 decision input, then emits batch-04-specific filenames and
version metadata. Its Markdown generator now explains the eight-create/two-hold result explicitly,
including both unresolved names. Earlier batch branches remain unchanged so batches 01 through 04
continue to reproduce from one validation implementation.

The generated `priority-2-batch-04-adjudicated-queue.json` uses copy-on-write rather than changing
the T40 checkpoint. It appends a fifth ordered decision event and recalculates cumulative counts.
The readable result explains the boundary for a non-code reviewer, while the manifest binds every
input and both outputs by SHA-256. This combination allows people to read the result and tests to
detect any later silent edit.

`test_fandom_priority_two_decisions_batch_four.py` adds six focused tests. They require exactly ten
decisions with eight creations and the two named holds, verify all twenty-three release rows stay
held, preserve every earlier decision group and history entry, and reproduce the frozen output.
Negative cases deliberately change an outcome, remove one family, reuse an earlier batch ID, and
try to promote a release variant. Each alteration must fail closed.

### Technical choices, alternatives, and trade-offs

The owner response is treated as bounded authorization because it followed a handoff that stated
the complete proposed split and named T42 as the next step. The decision file repeats that scope
instead of recording only “approved.” This makes later review possible without reconstructing the
conversation, although conversational attribution is still weaker than a cryptographic signature.

The Mazda and Nissan holds are preserved even though the current toy numbers point to the newer
Mazda and Tooned Nissan pages. Toy numbers help identify current rows, but the queued entity key is
still the shared display name. Automatically creating name-keyed families would encode collisions
with older or non-Tooned same-scale tools. The chosen hold sacrifices immediate coverage so later
materialization can introduce a tool-qualified name or lineage key deliberately.

The accepted outcomes are not materialized. Creating UUIDs or PostgreSQL rows in the same step
would combine two different decisions: whether the source evidence supports a family, and how that
family should be represented in searchable data. Separating adjudication from materialization
keeps rollback simple, avoids inventing release colors or canonical variants, and preserves the
Dual-RAG boundary. The trade-off is that accepted families are still not searchable.

### Decision changes

Eight T41 recommendations change from `pending` machine research into completed, attributable
`create_new_casting` decisions. The proposed Mazda MX-5 Miata and Nissan Skyline 2000GT-R LBWK
holds become completed owner holds; they are not discarded and remain visible for later identity
design. All ten decisions are family-only.

The cumulative state is now forty-four completed and nine pending family decisions. It contains
four accepted existing-family merges, thirty-six accepted new-family decisions, and four family
holds. Eighty-seven release rows fall under completed family decisions, but their variant state is
still hold and promotion eligibility remains zero. No canonical UUID, human-backed catalog entity,
PostgreSQL row, runtime behavior, calibration input, or evaluation label changed.

### Verification evidence

The focused T42 module passed 6/6, and decision checkpoints for batches 01 through 04 reproduced
byte for byte. The complete host suite passed 147/147 in 1.611 seconds on Python 3.14.6. The known
legacy-`httpx` Starlette TestClient warning remains limited to the machine-wide environment; the
constrained Python 3.12 runtime was already verified with `httpx2`.

The decision-file checksum is
`172775063922d1ab2ae999ddcea43a09826b02f4f01c97fbb1c3e0b9671c8dbf`; the cumulative queue is
`123e7432bc68710e9f3c6c01393b07456ff018c54619ea2111825c27f2ff5847`; the readable result is
`f83431ed2febf8607bb692a146142f0e874812bc9124e7ee1db1f16d9627eff3`; and the manifest is
`34c61547ea3ef76fd97fb46a54667272a99c2dce23f8c87568969d5df90136a9`. Final fixture, Wiki-pilot,
research, decision, compilation, Compose, and whitespace checks are captured in the T42 evidence
and QA review.

### Incomplete work, risks, and next step

Nine priority-2 families remain pending in the current 100-row pilot. The thirty-six accepted new-
family outcomes still lack stable review entity IDs and therefore are not part of either Dual-RAG
retrieval source. The two newest holds cannot be resolved safely with display-name equality; they
need a tool-qualified identity design.

The next immediate task is T43: use the checksum-verified T42 cumulative queue to research the
remaining nine pending families as the final bounded packet. T44 will require a separate owner
response. Only after all 53 family items have attributable outcomes should a new specification
design how accepted families become stable review entities and how larger yearly imports advance
toward approximately 3,000 reviewable variants.

## 2026-09-08 — Batch 04 separates same-name tools from retools and scale-qualified products

### What was executed and what problem it solves

T41 advances research from the exact T40 cumulative checkpoint. It verifies the latest queue and
manifest, skips all thirty-four completed decisions, and selects the next ten still-pending
priority-2 families in queue order. This keeps research aligned with actual adjudication state and
prevents earlier families from being selected again.

The batch covers twenty-three Wiki release rows across Lamborghini Huracán Sterrato, Max Steel,
Mazda Autozam, Mazda MX-5 Miata, Mazda REPU, Mercedes-Benz 500 E, Monster High Ghoul Mobile, Morgan
Super 3, Nerve Hammer, and Nissan Skyline 2000GT-R LBWK. Eight names have a dedicated casting
lineage plus non-Fandom exact-name corroboration and receive machine `create_new_casting`
recommendations. Mazda MX-5 Miata and Nissan Skyline 2000GT-R LBWK remain held because each display
name is reused by separate same-scale casting tools.

### Code changes and why they were made

`priority-2-batch-04-source-notes.json` records the bounded research input. Each family keeps its
stable queue ID, exact display name, a dedicated Wiki-page observation, and at least one concise
observation from another publisher. The non-Fandom evidence comes from Hot Wheels Collectors News,
All Hot Wheels, LastDodo, Football Stickipedia, Hot Wheels Database, and Diecast Radar. Only URLs
and paraphrased text claims are stored; no external images or full pages were copied.

The Mazda MX-5 record links the 2025 HYW18/HYX57 Chimera page to the separate 1991–2003 1:64 tool
2920 that uses the same displayed casting name. The Nissan record maps HYW79/HYY30/HYX54 to the
2024 Tooned page while retaining the regular 2022 HCW32 tool, which uses the same display name at
the same scale. Both are classified `homonymous_castings`, forcing family-level holds even though
the individual toy numbers explain which current page contains the staged rows.

Two contrasting cases are also made explicit. Nerve Hammer has multiple documented retools, but
one dedicated page treats them as a continuous lineage, so ordinary tooling revisions do not
create artificial families. Mercedes-Benz 500 E has a related Hot Wheels XL page, but that page is
explicitly suffixed and documents a 1:43 upscaled product; the queued releases and main page are
1:64. The relationship remains visible without turning a scale-qualified product into a false
same-tool conflict.

`build_fandom_priority_two_research.py` now accepts `--batch 4`, binding the build to
`priority-2-batch-03-adjudicated-queue.json` and its manifest and assigning batch-04 output names
and version metadata. The same builder still defaults to batch 01 and retains the explicit mappings
for batches 02 and 03, so all research batches share one validation policy without losing frozen
compatibility.

`test_fandom_priority_two_research_batch_four.py` adds six tests. They verify the next-ten queue
slice, ten-family/twenty-three-row/eight-create/two-hold totals, both conflicting pages and tool
numbers, two-host creation evidence, Mercedes scale context, Nerve Hammer retool continuity,
pending reviewer state, variant hold, zero promotion, checksums, and deterministic regeneration.

### Technical choices, alternatives, and trade-offs

Family identity remains stricter than release-page lookup. The Nissan toy numbers clearly identify
the Tooned page, and the Mazda numbers identify the 2025 page, but the current adjudication key is a
normalized display name intended for later retrieval. Accepting a name-only family while that same
name denotes another 1:64 tool would preserve the current rows but create an ambiguous future
entity. Holding the family costs review velocity but avoids encoding a collision that would later
need migration.

Retools are not automatically split. Treating every body/base revision as a new family would make
Nerve Hammer several identities even though the source catalog maintains one lineage. Conversely,
merging every exact display name would collapse the two Mazda and two Nissan tools. The chosen
method uses dedicated source-page lineage, scale, suffix, tool number, and exact queued name
together, rather than relying on text equality alone.

The research stays a ten-family bounded packet instead of crawling the remaining nineteen or a new
year in one run. Smaller batches keep sources and edge cases reviewable, but require more owner
round trips. That is appropriate in Lite mode because the highest-risk operation is identity
assignment, not fetching large quantities of strings quickly.

### Decision changes

No project-owner decision changed. The cumulative adjudication queue remains thirty-four completed
and nineteen pending families, including four existing-family merges, twenty-eight accepted new-
family decisions, and two holds. Sixty-four release rows under completed decisions remain variant-
held and promotion remains zero.

Within the unconfirmed research layer, eight families now have creation recommendations:
Lamborghini Huracán Sterrato, Max Steel, Mazda Autozam, Mazda REPU, Mercedes-Benz 500 E, Monster
High Ghoul Mobile, Morgan Super 3, and Nerve Hammer. Mazda MX-5 Miata and Nissan Skyline 2000GT-R
LBWK receive proposed holds. These statuses must not be counted as new human labels until T42
records an explicit owner response.

### Verification evidence

The T41 focused module passed 6/6. The complete host suite passed 141/141 in 1.491 seconds on the
available Python 3.14.6 interpreter. Fixture and 100-row Wiki-pilot validation, deterministic
review/queue/priority-one evidence, all four priority-two research batches, all three cumulative
priority-two decision checkpoints, Python compilation, default and PostgreSQL-profile Compose
configuration, and `git diff --check` all passed.

The batch-04 source-notes checksum is
`06616c879b3d8fa5d293338669b9497a29703a8055d44fce45c115e82efd6761`; research JSON is
`07ae79197f81f3595b5323a38834fbfd776fd7043180bd3f6961c3a03d2c9673`; the readable report is
`cb9ae7e45b670d64ae6c2d4831a13eee4d6a70d5f9edf3aa16a032f8a98415c4`; and the manifest is
`930f6bd72361501e93a792dae493d8b762325fe8df5a11625cd57f08b7a38923`. All four research `--check`
commands passed without changing the first three artifacts. The host suite emitted the documented
legacy-`httpx` Starlette TestClient warning on machine-wide Python 3.14; the constrained Python
3.12 runtime was previously verified with `httpx2`.

### Incomplete work, risks, and next step

All ten T41 reviewer blocks remain pending. The eight creation recommendations have no stable
review-catalog IDs and are not searchable through Dual-RAG. The two holds require a tool-qualified
family name or explicit lineage key; toy number alone does not repair the current name-key
collision. No color, release-level identity, catalog entity, PostgreSQL row, runtime behavior,
calibration data, or evaluation label changed.

The next immediate task is T42: present the exact eight-create/two-hold packet to the project owner
and, only if authorized, record it as a separate decision file. Nine priority-2 families will remain
after that batch, allowing one final bounded research packet before designing materialization and
the later expansion toward approximately 3,000 reviewable records.

## 2026-09-08 — Batch-03 research becomes an attributable owner decision layer

### What was executed and what problem it solves

T39 ended with an exact ten-family proposal and explained that the next step, T40, would accept
those `create_new_casting` recommendations only at casting-family scope. The project owner then
asked to execute that step. T40 records this bounded authorization instead of leaving it as an
implicit conversation state or pretending that machine research was already a human decision.

All ten T39 families are now completed owner decisions: Draftnator, Fiat 500e, Fish'd & Chip'd,
Ford Mustang GTD, Ford Performance SuperVan 4, Haulerback, Hirohata Merc, Kei Swap, Kick Kart, and
Kowloon'd Hypervan. Their eighteen release rows remain variant-held. The cumulative queue advances
from twenty-four completed / twenty-nine pending families to thirty-four completed / nineteen
pending, while promotion eligibility stays zero.

### Code changes and why they were made

`priority-2-batch-03-decisions.json` stores the authorization as its own immutable input. The batch
identifies `project_owner`, records the UTC decision time and conversational provenance, and covers
every frozen T39 packet exactly once. Each item repeats the approved `create_new_casting` outcome,
uses `casting_family_only` scope, leaves `target_family_id` null, holds variants, gives a
family-specific reason, and references both its packet and source evidence. Fiat 500e and Hirohata
Merc also retain the related-casting links that motivated T39's lineage boundary.

`apply_fandom_priority_two_decisions.py` now supports `--batch 3`. The new option binds the T38
cumulative queue and manifest, T39 research and manifest, and T40 decision file, then emits a
batch-03 queue, report, and checksum manifest. It reuses the existing validation path so the same
requirements apply to all priority-2 owner batches: exact packet coverage, outcome agreement,
valid reviewer/time/provenance, held variants, no existing-family target, evidence, and no duplicate
history ID.

The readable report previously described a fixed nine-create/one-hold split because that was true
for batches 01 and 02. The rendering branch now gives batch 03 accurate ten-create/zero-hold wording
without rewriting the two earlier reports. Batch 01 remains the default CLI behavior, batch 02 keeps
its original input mapping and Batman explanation, and checks prove their frozen bytes did not
change.

The derived `priority-2-batch-03-adjudicated-queue.json` is a copy-on-write checkpoint rather than
an edit to the T38 queue. Its manifest freezes every input and output hash. A new six-test module
checks the cumulative summary, all-ten approval, current eighteen-row variant hold, project-owner
attribution, preservation of the three prior batches and four-entry history, rejection of changed,
incomplete, and duplicate batches, and deterministic output reproduction.

### Technical choices, alternatives, and trade-offs

Approval remains an append-only adjudication layer instead of immediate materialization into
`human_backed_catalog.json`, the canonical fixture, or PostgreSQL. Immediate insertion would make
the newly researched names searchable sooner, but the owner only confirmed casting-family
existence. Stable entity IDs, alias policy, release grouping, color, and canonical variant identity
remain separate decisions. Preserving that boundary costs another later materialization step but
prevents family-level evidence from silently becoming variant ground truth.

The implementation continues to use one batch-aware applier instead of one script per batch. A
configuration-driven arbitrary batch engine was considered, but three explicit, validated CLI
choices remain easier to audit in Lite mode and fail closed on unknown filenames. Reuse reduces
drift in validation logic; the compatibility cost is handled by running `--check` on every earlier
batch whenever the shared code changes.

Complete batch coverage is mandatory even though all ten outcomes are identical. Allowing partial
application might look more flexible, but the owner's response referred to the displayed packet as
a whole. Requiring all ten exactly once proves that no family was silently omitted, substituted, or
assigned a wider scope. A batch ID already present in history is rejected to prevent accidental
double application.

### Decision changes

The ten T39 packets move from pending machine recommendations to completed project-owner family
decisions. No item changes its recommended outcome: all ten are accepted as new review-layer
casting families. This raises the cumulative accepted-new-family count from eighteen to
twenty-eight. The four earlier existing-family merges and the two earlier holds remain unchanged.

The history now contains four ordered owner events: priority 1, priority-2 batch 01, priority-2
batch 02, and priority-2 batch 03. Sixty-four Wiki release rows sit under completed family
decisions, but every one still has a variant hold. Therefore the catalog size, PostgreSQL contents,
Dual-RAG candidate sources, calibration data, evaluation labels, and runtime outputs are unchanged.

### Verification evidence

The T40 focused suite passed 6/6. It verified 34 completed / 19 pending families, 4 merges, 28
accepted new-family decisions, 2 holds, 64 held release rows, four ordered decision batches, and
zero promotion. Negative cases altered a creation to a hold, removed one decision, and reused the
batch-02 ID; all failed closed.

The complete host suite passed 135/135 in 1.425 seconds on the available Python 3.14.6 interpreter.
Fixture and 100-row Wiki-pilot validation, deterministic review/queue/priority-one evidence, all
three priority-two research batches, all three cumulative priority-two decision checkpoints,
Python compilation, default and PostgreSQL-profile Compose configuration, and `git diff --check`
all passed. The known machine-wide Starlette TestClient warning for legacy `httpx` remains; the
project's constrained Python 3.12 runtime was previously verified with `httpx2`.

The owner decision checksum is
`ecd3af4c0b003d3458e719109eff9b41c546787d3cd5c5bb5d313dd4d316dd8c`; the cumulative queue is
`edee360faccb43b4bea58a91d5be67b511d9e41ea6a76f21ec4648bae83190b9`; the readable result is
`523af3b17045ee2f3322fdad57d5666f9fbc0c634d957aad7c32e32bc41d7bde`; and the manifest is
`8adc3ba56d7b55e03958de335c2c8a82c351094636fd496d54cd430422b00704`.

### Incomplete work, risks, and next step

Conversation provenance is auditable in the repository but is not a cryptographic signature. The
twenty-eight accepted new families still have no stable review-catalog IDs and cannot be retrieved
by either Dual-RAG source. The sixty-four held release rows have not gained verified color or
canonical variant identity, and no new PostgreSQL-scale accuracy or latency evidence was produced.

The next immediate task is T41: research the next ten of nineteen pending priority-2 families from
the new T40 cumulative queue using the same two-source, disambiguation, homonym, and related-lineage
safeguards. Only after all priority-2 family decisions are attributable should the project design
how accepted families become stable review-catalog entities before expanding toward the planned
3,000-row dataset.

## 2026-09-08 — Batch 03 researches related castings without turning research into approval

### What was executed and what problem it solves

T39 advances the external-data review from the T38 cumulative checkpoint rather than returning to
the original 53-family queue. It verifies the latest queue checksum, skips all twenty-four
completed family decisions, and researches the next ten pending priority-2 families in their
existing deterministic order. This prevents duplicate work and keeps every new conclusion tied to
the exact adjudication state that produced it.

The batch covers eighteen 2025 Wiki release rows across Draftnator, Fiat 500e, Fish'd & Chip'd,
Ford Mustang GTD, Ford Performance SuperVan 4, Haulerback, Hirohata Merc, Kei Swap, Kick Kart, and
Kowloon'd Hypervan. Each name has a dedicated Hot Wheels Wiki casting page and at least one
non-Fandom source confirming the exact casting name. The resulting packet therefore recommends
ten `create_new_casting` family outcomes and zero holds. These are deliberately still machine
recommendations: reviewer confirmation remains pending, all eighteen release variants remain
held, and promotion eligibility remains zero.

### Code changes and why they were made

`priority-2-batch-03-source-notes.json` is the structured research input. Every record repeats the
stable family review ID and exact queue name, then stores a concise observation from the dedicated
Wiki page and a separate exact-name observation from another publisher. The sources include Orange
Track Diecast, All Hot Wheels, South Texas Diecast Collectors, Hot Wheels Collectors News, Old Cars
Weekly, and Hot Wheels Database. Only HTTPS URLs and short paraphrased claims are stored; no images
or full third-party pages were copied into the repository.

Two records preserve extra identity context. Fiat 500e retains the separate Fiat 500 page so a
future reviewer does not collapse the electric-model casting into a nearby name. Hirohata Merc
retains the older `'51 Merc` page and a source explanation that the current mainline release uses a
newer tool. The code classifies both current exact names as `single_casting` because neither queued
name is shared by the related tool. This differs from the batch-02 Batman case, where separate tools
use the same display name and must remain held.

`build_fandom_priority_two_research.py` now accepts `--batch 3`. That option binds the research to
`priority-2-batch-02-adjudicated-queue.json` and its manifest, applies the existing rule to the first
ten still-pending priority-2 families, and emits batch-03-specific JSON, Markdown, and manifest
files. The default remains batch 01 and batch 02 keeps its previous input mapping, so the extension
does not alter earlier frozen artifacts or introduce a second implementation with different
validation behavior.

`test_fandom_priority_two_research_batch_three.py` adds six focused tests. They prove that batch 03
is exactly the next ten items after T38; freeze the ten-family, eighteen-row, ten-create result;
require Fandom plus a distinct source host; retain both related-casting distinctions; keep every
reviewer, variant, and promotion boundary closed; and reproduce the JSON, report, manifest, and
hashes byte for byte.

### Technical choices, alternatives, and trade-offs

The project continues to use a small, auditable source packet rather than a broad autonomous web
crawl. A crawler could gather more pages quickly, but it would increase licensing, page-quality,
rate-limit, and identity-matching risks before the current 100-row workflow is fully adjudicated.
The bounded approach costs manual research time but makes the exact evidence and transformation
easy to review and reproduce in Lite mode.

The creation rule remains a dedicated Wiki page plus exact-name evidence from at least one
publisher outside Fandom. This is not a claim that collector sites are authoritative for every
paint, base, or release detail; it is a cross-source check that the casting name is not merely an
unmatched string in the local catalog. Requiring manufacturer-only documents was considered too
restrictive for historical and fantasy models, while accepting Fandom alone would create a
single-source failure point.

Related pages are treated as lineage evidence rather than a universal hold trigger. Automatically
holding every related casting would block legitimate uniquely named tools such as Fiat 500e and
Hirohata Merc. Automatically merging them would erase physical-tool distinctions. The chosen rule
looks at whether the exact queued display name uniquely selects the current tool, while recording
the related page for later human review. The trade-off is that this remains text-source identity
evidence, not inspection of the physical casting.

### Decision changes

No project-owner decision changed in T39. The cumulative adjudication state remains twenty-four
completed and twenty-nine pending families, with four existing-family merges, eighteen accepted
new-family decisions, two holds, forty-six held variants under completed decisions, and zero
promotion. Batch 03 is a separate research artifact layered on top of that unchanged state.

What did change is the research policy's documented boundary. Batch 02 established that distinct
tools sharing one display name must be held. Batch 03 now records the complementary case: a related
or predecessor tool with a different stored name does not automatically invalidate a unique exact
current name. The relation must remain visible, but a family creation recommendation can proceed
when the current identity still meets the two-source rule.

### Verification evidence

The new T39 module passed 6/6. The complete host suite passed 129/129 in 1.499 seconds on the
available Python 3.14.6 interpreter. Fixture and 100-row Wiki-pilot validation, deterministic
review/queue/priority-one evidence, all three priority-two research batches, both cumulative
priority-two decision checkpoints, Python compilation, default and PostgreSQL-profile Compose
configuration, and `git diff --check` all passed.

The batch-03 source-notes checksum is
`6f2753b7e736145970096660ba07ce4553ebd423b1f551c7780dc7b91274cf86`; research JSON is
`1d38a7bbffbf905283d4c7be6a24495547df425723ef610539c1f3eee07c432d`; the readable report is
`44472564cac68bb3073c0ceeab2dbc663994cb859318a7cab5f5f0f5b3d4c940`; and the manifest is
`92dae730213f9928dd5811d8a43657038a037bd85462653fc2639db44a33e97b`. All three research-batch
`--check` commands passed without changing the two earlier hashes. The host suite emitted the
already documented legacy-`httpx` Starlette TestClient warning on machine-wide Python 3.14; the
project's constrained Python 3.12 runtime was previously verified with `httpx2`.

### Incomplete work, risks, and next step

The ten recommendations have not been approved by the project owner and are not searchable family
entities. None has a stable review-catalog ID, verified color, canonical release variant, or
PostgreSQL row. Remote source pages can change after the recorded research date, and the stored
paraphrases do not replace physical-casting verification.

The next immediate task is T40: present this exact frozen ten-family result to the project owner.
Only an explicit response to that packet should be translated into a separate attributable
batch-03 decision file. If approved, the decision applier can then derive a new cumulative queue
while still keeping all release variants and catalog/database promotion held.

## 2026-09-08 — Batch-02 recommendations become attributable owner family decisions

### What was executed and what problem it solves

T37 produced ten source-backed recommendations but intentionally left every reviewer field
pending. The project owner then asked to execute the explicitly stated next step after being shown
the exact outcome: accept nine `create_new_casting` recommendations and keep `Batman and Robin
Batmobile` held. T38 records that bounded authorization and applies it to the latest cumulative
queue.

This solves two different audit problems. First, a machine recommendation is no longer confused
with the owner's choice: the recommendation file remains unchanged and the approval has its own
actor, time, provenance, reasons, and evidence. Second, batch 02 does not overwrite the fourteen
earlier decisions. The resulting checkpoint contains twenty-four completed family decisions and
twenty-nine pending families while retaining the full three-event decision history.

### Code changes and why they were made

`priority-2-batch-02-decisions.json` records the `project_owner` decision batch at
`2026-09-08T18:55:38Z`. It covers every T37 family exactly once. Nine records accept
`create_new_casting`; the Batman record accepts `hold` and cites both the current page and the
separate 2004 100% Hot Wheels tool page. Every record says `casting_family_only`, leaves
`target_family_id` null, holds release variants, provides a family-specific reason, and links to
its frozen research packet plus source evidence.

`apply_fandom_priority_two_decisions.py` was generalized from a batch-01-only command to a
batch-aware applier. `--batch 2` binds the T36 cumulative queue, T37 research and manifest, and the
new owner decision file. It derives batch-02-specific queue/report filenames and version metadata.
The validation method now receives the actual research filename so evidence references cannot
silently point to batch 01.

The history logic was also corrected for a true cumulative input. Batch 01 begins with a legacy
single `decision_batch` object and converts it to a list; batch 02 begins with the existing
`decision_batches` list. The applier now accepts either representation, preserves every prior item,
and appends the current batch. It rejects a malformed prior history instead of replacing it. The
same batch ID is also rejected if it already exists in history. The default batch-01 behavior and
frozen report wording remain unchanged, while batch 02 renders the Batman-specific unresolved
lineage.

The derived `priority-2-batch-02-adjudicated-queue.json`, readable result, and manifest capture the
new cumulative state and checksum every input/output. A dedicated six-test module checks counts,
the nine-create/one-hold split, attribution and scope, preservation of both earlier decision sets,
three-entry history, fail-closed changed/incomplete batches, and deterministic regeneration.

### Technical choices, alternatives, and trade-offs

Approval is kept as an append-only decision layer rather than inserted directly into
`human_backed_catalog.json` or PostgreSQL. This means accepted families are not searchable yet,
which is a deliberate cost: family existence, stable entity materialization, and release-variant
identity are separate claims with different evidence. The current owner response authorizes only
the first claim.

The applier reuses one validated implementation for both priority-2 batches instead of copying a
nearly identical batch-02 script. Reuse reduces divergent validation rules, but it requires
explicit batch configuration and backward-compatibility checks. Both batch outputs are therefore
tested byte for byte. A fully generic arbitrary-batch configuration file was considered
unnecessary at two batches; adding only the two validated CLI choices keeps Lite scope small and
prevents accidental application against an unreviewed filename.

Complete ten-packet coverage remains mandatory. A partial approval format could support more
granular owner choices, but the actual authorization referred to the entire displayed proposal.
Requiring all ten exactly once ensures that the hold is recorded rather than silently omitted and
that no creation outcome changes while the batch is applied.

### Decision changes

Nine T37 families have moved from machine recommendation to completed project-owner family
decisions: `'94 Audi Avant RS2`, `Alpha Pursuit`, `Bogzilla`, `Crescendo`, `Custom '53 Chevy`,
`Custom Cadillac Fleetwood`, `Deora III`, `DMC DeLorean`, and `Donut Drifter`. `Batman and Robin
Batmobile` has moved from proposed hold to an accepted hold because HYW60/HYX61 still lack a
tool-specific mapping.

Across all owner batches, the cumulative state is now four accepted existing-family merges,
eighteen accepted new-family decisions, and two held family decisions. Twenty-nine families remain
pending. Forty-six release rows belong to completed family decisions, but all forty-six remain
variant-held and no family is promotion eligible. These numbers describe the adjudication layer,
not a catalog-size increase.

### Verification evidence

The combined batch-01 and batch-02 focused decision suite passed 12/12. It verified 24 completed /
29 pending counts, 4 merges, 18 accepted new families, 2 holds, 46 held releases, and zero
promotion. It also proved that the current batch contains exactly nine creations plus the Batman
hold, all records are attributable and family-only, the prior four plus ten decisions remain
unchanged, and history has three ordered entries.

Negative tests changed an approved creation to hold, removed one decision, and reused the prior
batch ID; the applier rejected all three cases. Batch-01 and batch-02 `--check` commands both
passed. The new cumulative queue checksum is
`81911e948fd00e76e6da7255ab1174c1697871ac59c3bf674dc5bae645fbc497`; the report checksum is
`f6bad5ae831d17bf1ab279c55a46a0dfe176755acfb8c20f512c504af884a392`; and the owner decision file
checksum is `7350ad739d80999690a74ca1713e86e9509f3c88b038158da45a25e67f094481`.

The complete host suite passed 123/123 in 1.422 seconds on the available Python 3.14.6
interpreter. Fixture and Wiki-pilot validation, T31–T38 deterministic regeneration, Python
compilation, default and PostgreSQL-profile Compose configuration, and `git diff --check` all
passed. The host suite emitted the already documented Starlette TestClient warning because the
machine-wide Python 3.14 environment exposes legacy `httpx`; the previously verified constrained
Python 3.12 runtime uses `httpx2` warning-free. This task did not execute PostgreSQL, change
resolver behavior, or add evaluation labels.

### Incomplete work, risks, and next step

Conversation provenance is auditable in this repository but is not a cryptographic signature.
The eighteen accepted new-family decisions across both batches still lack stable catalog entity
IDs, and no accepted family can be returned by the runtime. The Batman hold is unresolved at the
tool level, and no release has verified color or canonical variant identity.

The next immediate task is T39: research the next ten of twenty-nine pending families using the
T38 cumulative queue. After all priority-2 families have attributable outcomes, a separate
materialization design can decide how accepted family entities enter the review catalog without
inventing release data or bypassing canonical review.

## 2026-09-08 — Batch 02 advances the queue and catches a same-name casting conflict

### What was executed and what problem it solves

T36 left a cumulative review queue with fourteen completed family decisions and thirty-nine still
pending. T37 continues the research from that exact checkpoint. It selects the first ten pending
priority-2 families in the T36 queue, examines one casting-specific Hot Wheels Wiki page plus at
least one publisher outside Fandom for each name, and emits a new frozen review packet. This avoids
both re-researching the ten batch-01 families and treating “not found in our small catalog” as
proof that a new casting should be created.

The observable result is a ten-family / eighteen-release batch. Nine names have sufficient
two-source, exact-name evidence for a machine `create_new_casting` recommendation. The tenth,
`Batman and Robin Batmobile`, demonstrates why exact text is not enough: the current mainline name
is also used by a separate 2004 100% Hot Wheels casting tool G5513. That family remains held until
the staged releases can be mapped to a tool-specific lineage. All ten reviewer confirmations are
still pending, every release variant is held, and promotion eligibility remains zero.

### Code changes and why they were made

`priority-2-batch-02-source-notes.json` is the human-readable research input in structured form. It
keeps the queue family ID and exact name beside concise observations and HTTPS evidence. Sources
include Mattel Consumer Services and independent collector/catalog publishers such as Orange Track
Diecast, 164Custom, Hot Wheels Collectors News, Hot Wheels Database, and HW Treasure. The Batman
record additionally stores the related 2004 page and its G5513 distinction, so the hold is based on
an explicit conflicting identity rather than a vague lack of confidence.

`build_fandom_priority_two_research.py` was extended from a batch-01-only command to a shared
batch-aware builder. `--batch 2` binds the input to
`priority-2-batch-01-adjudicated-queue.json` and its manifest, then names the outputs with the
batch-02 prefix and version. Default invocation remains batch 01, so the existing frozen contract
and checksums remain compatible. The validator now accepts `homonymous_castings` as a distinct
source classification and maps it to a mandatory hold; the older `disambiguation` wording remains
unchanged so batch 01 reproduces byte for byte.

The generated JSON stores the ten machine recommendations, complete source rows, evidence hosts,
pending reviewer blocks, and explicit family-versus-variant scope. The Markdown report presents
the same information for owner review. The manifest binds the T36 queue, its manifest, the new
source notes, research JSON, and report with SHA-256 checksums. A dedicated six-test module verifies
later-batch selection, counts, evidence hosts, the Batman homonym, non-promotion boundaries, and
deterministic outputs without weakening the six existing batch-01 tests.

### Technical choices, alternatives, and trade-offs

The later batch reads the latest cumulative queue instead of the original T34 queue. A manual
“skip the first ten” convention would be shorter code, but it would become wrong as soon as a hold
is revisited or batches are applied in a different order. Selecting records whose actual reviewer
status is still `pending` lets the decision artifact, rather than positional memory, define what
work remains. The trade-off is that each research batch is cryptographically coupled to the latest
queue checkpoint and must be rebuilt or deliberately migrated if that upstream artifact changes.

The evidence policy remains two-source rather than manufacturer-only. Manufacturer documentation
is preferred where available, but historical and fantasy castings are often documented more
completely by established collector catalogs. Requiring an exact-name corroboration outside
Fandom reduces single-source dependence without falsely claiming those publishers independently
verified every physical detail. Remote pages can change, which is why the repository freezes URLs,
claims, date, transformed outputs, and checksums rather than pretending it owns an immutable copy
of every source page.

`homonymous_castings` is separate from `disambiguation`. A disambiguation page openly lists several
tools under one title; a homonym can have a dedicated page for the current tool while another page
uses effectively the same display name. Treating both as safe creations would collapse physical
lineages. Treating every related scale or premium release as a conflict would be overly strict, so
the hold is used only where evidence shows a separate casting tool with the same name; Donut
Drifter's separately named Hot Wheels XL product, for example, does not erase the dedicated 1:64
identity.

### Decision changes

Before T37, the builder understood only a dedicated single-casting page or an explicit
disambiguation page, and only batch 01 could be selected from the command line. It now models a
third failure-safe case—distinct tools sharing a display name—and can deterministically build
either research batch from its proper upstream queue. This is a schema-compatible extension:
batch-01 data and output hashes did not change.

Nine new names now have source-backed machine recommendations, but none has moved to completed
review status: `'94 Audi Avant RS2`, `Alpha Pursuit`, `Bogzilla`, `Crescendo`, `Custom '53 Chevy`,
`Custom Cadillac Fleetwood`, `Deora III`, `DMC DeLorean`, and `Donut Drifter`. Batman and Robin
Batmobile is explicitly held. The cumulative adjudication queue itself remains at fourteen
completed / thirty-nine pending because research does not impersonate an owner decision.

### Verification evidence

The combined batch-01 and batch-02 focused suite passed 12/12. It proves that batch 02 equals the
next ten pending items in the T36 queue and excludes a completed batch-01 family; that the output
contains ten families, eighteen rows, nine proposed creations, and one homonymous hold; that the
separate 2004 G5513 tool is retained in evidence; that creation recommendations span Fandom plus a
different host; and that all reviewer, variant, and promotion boundaries remain closed.

Both `python3 scripts/build_fandom_priority_two_research.py --batch 1 --check` and `--batch 2
--check` passed. The batch-02 research checksum is
`e0814c8017361049c2fa3b712198a22968e9818c2db273c49af668c2639050dc`; its readable report checksum
is `86444256ded953b6ed5e329dccfdf531e5f2565df7212370178fb1a45d81a7ca`; and its upstream T36 queue
checksum is `2b82ca5023439857f186aa0ab122f0b4511290bb4d1303ac533df5c96fbc6790`.

The complete host suite passed 117/117 on the available Python 3.14.6 interpreter. Fixture and
Wiki-pilot validation, T31–T37 deterministic regeneration, Python compilation, default and
PostgreSQL-profile Compose configuration, and `git diff --check` all passed. The host suite emitted
the already documented Starlette TestClient deprecation warning because this machine-wide Python
3.14 environment still exposes legacy `httpx`; the project's constrained Python 3.12 environment
uses `httpx2` and was previously verified warning-free. T37 changed no runtime dependency, and this
research run does not upgrade web-page review into live database or resolver evidence.

### Incomplete work, risks, and next step

These are AI-assisted research recommendations, not human labels. Source accuracy and future page
changes remain risks, and the Batman evidence proves only that the name is ambiguous between tools;
it does not yet prove which tool HYW60 and HYX61 represent. No accepted catalog family, stable
entity ID, canonical variant, PostgreSQL row, or searchable Dual-RAG record was created.

The next immediate task is T38: present this exact ten-item batch to the project owner, record the
owner's accept/hold decisions in a separate attributable file, validate complete agreement and
scope, and derive a new cumulative queue. Only then should batch 03 select the next pending ten.

## 2026-09-08 — Owner approval converts batch-01 research into ten attributable family decisions

### What was executed and what problem it solves

T35 answered the research question for ten possible-new families, but deliberately left the
reviewer fields empty. The project owner then asked to execute the stated next step after being
shown the exact proposal: approve nine `create_new_casting` family outcomes and keep `'55 Chevy`
on hold. T36 records that response as a separate decision event and calculates the new cumulative
queue state.

This closes the gap between “a machine found supporting sources” and “the project owner accepted
the family decision.” It also prevents the short approval message from being interpreted too
broadly. The resulting authority covers exactly the ten displayed recommendations and only casting
family identity; it does not approve colors, releases, canonical UUIDs, database rows, or the other
39 families.

### Code changes and why they were made

`priority-2-batch-01-decisions.json` records the stable batch ID, `project_owner` role, UTC time,
conversation provenance, and ten decisions. Each item cites its T35 research packet and external
evidence, states a family-specific reason, uses `casting_family_only`, has no existing-family
target, and keeps `variant_decision=hold`.

`apply_fandom_priority_two_decisions.py` verifies both the T34 queue checksum and T35 research
checksum before accepting the decision file. It requires valid batch attribution, unique complete
coverage of all research packets, an outcome identical to the approved recommendation, a direct
packet reference, family-only scope, and variant hold. For each creation it rechecks that the Wiki
page was classified as one casting, at least one independent source exists, evidence spans two
hosts, and the earlier exact-match indexes contain no catalog family.

The applier deep-copies the T34 queue and preserves its four priority-1 merge decisions. It replaces
the older single batch field with an ordered two-entry decision history, applies the ten new
decisions, recalculates cumulative counts, and writes a new batch-specific queue, Markdown result,
and checksum manifest. The older all-pending and T34 four-decision queues remain unchanged, so each
stage can be reproduced and compared.

### Technical choices, alternatives, and trade-offs

The code treats approval as an append-only decision layer instead of immediately materializing
nine catalog objects. This adds another artifact in the chain, but it keeps three very different
claims separate: a family probably exists, the owner accepts that conclusion, and a canonical
variant is safe for runtime matching. Collapsing those claims would make source review look like
product-level ground truth.

Complete batch coverage is required rather than accepting a partial list. The user's authorization
referred to the previously displayed ten-item proposal as one set, so all ten outcomes must be
present exactly once. A future correction can use another explicit decision event; silently
dropping an item or changing one recommendation during application is rejected.

The new output has an explicit filename rather than overwriting `adjudicated-queue.json`. This is
slightly more verbose for downstream scripts, but it gives Git a clear audit trail and lets T37
select from the true latest queue without destroying the T34 checkpoint.

### Decision changes

Nine families have moved from machine recommendation to accepted project-owner decisions: 1988
Jeep Wagoneer, 2020 Ram 1500 Rebel, `'21 Ford Bronco`, `'22 Ford Maverick Custom`, `'66 Buick
Riviera`, `'69 Corvette Racer`, `'80 El Camino`, `'87 Audi quattro`, and `'90 Honda Civic EF`.
`'55 Chevy` has moved from proposed hold to an accepted hold because the exact casting lineage is
still unresolved.

The cumulative review queue now contains fourteen completed decisions: four merges from T34, nine
new-family decisions, and one hold. Thirty-nine priority-2 families remain pending. This is not yet
a catalog-count increase; the nine accepted families still exist only as decisions attached to
their source rows.

### Verification evidence

Six focused tests verify the 14/39 cumulative counts, nine-create/one-hold batch, attribution,
family/variant boundary, preservation of all four earlier merges and both decision batches,
fail-closed changed outcome, fail-closed incomplete coverage, hashes, and deterministic rebuild.
The first focused run failed because the new test expected the wrong historical Priority 1 batch
ID. Inspection showed that the product data correctly retained
`fandom-2025-priority-1-owner-confirmation-v1`; the test expectation was corrected and all focused
tests then passed 6/6.

The complete host suite passed 111/111. Fixture and Fandom staging validation, T31–T36 deterministic
checks, Python compilation, default and PostgreSQL Compose configuration, and whitespace checks all
passed. The new cumulative queue checksum is
`2b82ca5023439857f186aa0ab122f0b4511290bb4d1303ac533df5c96fbc6790`; its readable report checksum
is `fe00de56e8c425fa5f80c06722deb702f4fb357d1e40495efb4548830bcfaff9`.

### Incomplete work, risks, and next step

The conversation provenance is auditable inside the repository but not a cryptographic signature.
The underlying external sources can also change. More importantly, the accepted creations have not
been assigned separate catalog entity IDs or made searchable; doing so safely needs its own schema
and must not turn unknown release colors into canonical variants.

The next immediate task is T37: use the T36 cumulative queue to research the next ten of the 39
pending priority-2 families. Keeping research and adjudication in repeated small batches will expose
more ambiguous names before any larger catalog materialization or 3,000-row ingestion begins.

## 2026-09-08 — The first ten possible-new families now have bounded source evidence

### What was executed and what problem it solves

T34 left 49 priority-2 names in the honest state “not found in our current catalogs.” That state
does not prove a name represents a new casting: it can also mean the local catalog is incomplete,
the name is an alias, or one display name hides several physical casting tools. T35 researches the
first ten pending families in the adjudicated queue instead of treating absence as proof.

The research found nine names that each resolve to one dedicated Hot Wheels Wiki casting page and
also appear under the exact Hot Wheels casting name at a publisher outside Fandom. It also found a
counterexample that validates the need for this step. `'55 Chevy` is a disambiguation title for
three distinct tools introduced in 1982, 1998, and 2006; creating one family from that name would
erase a real identity distinction. Batch 01 therefore proposes nine `create_new_casting` outcomes
and one `hold`, while leaving all ten reviewer confirmations pending.

### Code changes and why they were made

`priority-2-batch-01-source-notes.json` records the bounded research input: stable queue ID, exact
casting name, dedicated Wiki page classification, non-Fandom publisher, source type, HTTPS URL,
and a concise paraphrase of the observed claim. The file states that the process was AI-assisted
and does not attribute any identity decision to a human. It stores text notes only and downloads no
images.

`build_fandom_priority_two_research.py` first verifies that the derived T34 queue still matches its
manifest. It then selects exactly the first ten priority-2 families whose reviewer status is still
pending. The source notes must cover those same IDs and names in the same order. Each family must
have a Fandom casting-page classification and at least one exact-name source from another host; a
Fandom URL presented as “independent” is rejected.

The recommendation is derived from this narrow rule rather than typed into the notes. One
`single_casting` page plus the independent confirmation yields `create_new_casting`; a
`disambiguation` page yields `hold`. The generated JSON, readable Markdown report, and manifest
preserve the 19 staged release rows, source links, decision reason, pending reviewer block, variant
hold, and zero promotion eligibility. Six tests lock selection, counts, the `'55 Chevy` exception,
source independence, fail-closed behavior, checksums, and deterministic regeneration.

### Technical choices, alternatives, and trade-offs

A two-source rule was chosen because the yearly list and each casting page share the same community
ecosystem. Requiring another publisher does not make the evidence infallible, but it is materially
stronger than copying a name from one table. Manufacturer evidence is preferred when available;
established collector databases and archived Hot Wheels case documents are used for older or less
visible models where a current Mattel product page is not available.

The batch size is ten so a non-programmer can inspect the report without reviewing all 49 names in
one sitting. The cost is more batches and manifests. That cost is intentional: small diffs make it
easier to notice exceptions such as the three `'55 Chevy` tools before an incorrect family becomes
part of the catalog.

Remote pages were not copied wholesale. The repository freezes concise observations and URLs,
which avoids unnecessary third-party content duplication and keeps the evidence readable. The
trade-off is that a later audit may find that a remote page has changed or disappeared; the research
date and checksummed notes make that limitation visible instead of implying a permanent snapshot.

### Decision changes

Before T35, all 49 unmatched groups had the same undifferentiated “research required” state. The
first ten now have evidence-backed machine recommendations, but they have not become reviewer
decisions. This distinction matters: the project owner has not yet accepted the nine creations or
the one hold, so the adjudicated queue correctly continues to show 49 pending priority-2 decisions.

The identity boundary is unchanged. A proposed family creation answers only whether a distinct
casting family appears to exist. It does not validate the 2025 color, series, collector number,
toy-number release identity, or any canonical UUID. All 19 release rows therefore remain held.

### Verification evidence

The new batch contains exactly 10 families and 19 Wiki rows in deterministic queue order. Nine
packets propose `create_new_casting`; the single `hold` is `'55 Chevy`. All packets have at least
two distinct source hosts, reviewer status `pending`, variant decision `hold`, and
`promotion_eligible=false`. The focused tests passed 6/6, and the full host suite passed 105/105.

Fixture validation, Wiki staging validation, T31–T35 deterministic checks, Python compilation,
both default and PostgreSQL Compose configurations, and whitespace checks passed. The research JSON
checksum is `a802f64478b73a0c40f43c1d43fa44b182ebdbcde9f67d3d0c97f237c92a241c`; the readable report
checksum is `acdd94dc89abee72f0c2e197bf4392fc2c13671b2282cc68e5765d6dbca9669f`.

Ruff and mypy were not rerun in this host session because they are not installed in the global
Python environment and the sandboxed `uv` attempt could not reach PyPI. This did not prevent the
105-test suite, compilation, data validators, deterministic checks, Compose checks, or whitespace
check from completing.

### Incomplete work, risks, and next step

The strongest remaining risk is confusing source agreement with owner approval. Collector sources
can repeat each other's errors, and the remote pages are not immutable. The nine recommendations
are suitable for an explicit family-level review, not for automatic canonical promotion. The
`'55 Chevy` rows need additional identifier evidence that maps the 2025 release to one of the three
known casting lineages.

The next step is to present these ten outcomes to the project owner for acceptance or correction.
Once the owner provides an explicit decision, a priority-2 decision applier can record the nine
family creations and one hold—still with all release variants held. Batch 02 can then research the
next ten of the 39 priority-2 families not yet examined.

## 2026-09-08 — Four owner-approved family links are recorded without variant promotion

### What was executed and what problem it solves

T33 ended with a precise proposal: connect four exact-name Wiki groups to their existing
human-backed casting families, but keep all nine release variants held. The project owner then asked
to execute the next step. T34 records that follow-up authorization as an auditable decision batch
and applies it through a validator rather than silently editing generated queue data.

The resulting state now distinguishes three facts. Four casting-family relationships are completed
decisions; 49 possible-new-family decisions remain pending; and none of the Wiki releases is a
verified canonical variant. This lets the project honestly say some manual family review has
occurred without overstating the catalog or changing Dual-RAG output.

### Code changes and why they were made

`priority-1-decisions.json` records a batch ID, `project_owner` reviewer role, UTC timestamp,
conversation provenance, and four family-specific decisions. Each includes the stable family-review
ID, exact human target, `casting_family_only` scope, `variant_decision=hold`, a reason explaining
the release differences, and references to the evidence packet, human family, and every relevant
Wiki source row.

`apply_fandom_adjudication_decisions.py` validates both upstream checksums before reading the batch.
It requires a supported schema, named batch/reviewer, valid UTC timestamp, provenance, unique known
family IDs, permitted outcome, written reason, evidence references, family-only scope, and variant
hold. For a merge, the target must already be one of that family's exact pre-review candidates.
The original all-pending queue is deep-copied rather than modified.

The derived `adjudicated-queue.json` marks those four reviewer decisions completed, retains all
other entries as pending, and keeps `promotion_eligible=false` everywhere. A readable result and
manifest capture the 4 completed / 49 pending / 9 variant-held / 0 promotion-eligible counts and
freeze the queue, evidence, decision input, and outputs. Tests also inject a wrong merge target and
prove that application fails closed.

### Technical choices, alternatives, and trade-offs

Decisions are stored as data separate from both the machine-generated queue and the resulting
state. This event-like design adds files, but it preserves the before state, reviewer action, and
after state independently. Editing `adjudication-queue.json` in place would be shorter yet destroy
deterministic regeneration and make it hard to tell whether a field came from code or a reviewer.

The reviewer is recorded as the role `project_owner`, not an invented personal name. The provenance
accurately states that the owner requested execution after receiving the explicit merge/hold
proposal. This is traceable repository evidence, although it is not a cryptographic signature or
external identity proof.

Completing a family merge still does not make the family promotion eligible. That may look
conservative, but the human target is itself provisional and the Wiki rows still lack verified
colors. The accepted outcome is therefore a knowledge relationship inside the review layer, not a
new canonical entity.

### Decision changes

T32's queue contract allowed four outcomes, while T34 deliberately narrows this particular batch to
family scope with variant hold. This prevents a broadly worded follow-up request from accidentally
granting release-level approval. Future priority-2 batches may use create/hold/reject, but they must
pass their own evidence requirements.

The project also moves from “zero human decisions” to “four project-owner family decisions,” while
leaving the accuracy/evaluation boundary unchanged. Documentation now distinguishes family linkage,
variant verification, canonical promotion, and evaluation labels as separate states.

### Verification evidence

Four completed decisions target the exact human candidates for `'67 Chevy C10`, `Purple Passion`,
`Subaru BRZ`, and `Tesla Model S Plaid`. Forty-nine decisions remain pending. Nine Wiki release
variants remain held, and promotion-eligible and newly canonical records both remain zero.

The decision checksum is
`ef17632c486850ab8f39604462e474c8c0e97894a8a8fc0003aef58b5fab03f0`; the adjudicated queue
checksum is `6ab11ddef990e31918e507372c451cc0bfce531d7c9ec41e91ecc680288d0082`;
the readable result checksum is
`bd916df6b82866f87766c5ab038646d6aee90c4dd69e93a57120aef91cbaf023`.

Five focused tests passed, including the invalid-target failure. The complete host suite passed
99/99. T30–T33 deterministic checks, fixture validation, Python compilation, both Compose
configurations, and whitespace checks passed. T34 made no network request, PostgreSQL write,
canonical catalog edit, runtime change, or AI-evaluation mutation.

### Incomplete work, risks, and next step

The four relationships point to a provisional human-backed catalog, not the canonical catalog.
They cannot yet answer which 2025 toy number corresponds to which color or whether a Wiki release
matches the existing human provisional variant. The conversation-based owner provenance is
auditable but not signed.

The remaining work is the 49 priority-2 families. Before any `create_new_casting` decision, the
project needs independent text-source confirmation that the normalized Wiki name is a real distinct
casting rather than an alias, punctuation difference, or incomplete catalog coverage. That research
should be performed in bounded batches before any database scaling.

## 2026-09-08 — Four side-by-side packets make the first decisions reviewable

### What was executed and what problem it solves

T32 created a clean 53-family queue, but the four priority-1 entries still pointed to IDs rather
than showing why a reviewer should accept or reject them. T33 assembles the evidence needed for
those first bounded decisions. For each exact-name family it places every Wiki release row beside
the retained human label, original source name when available, structured series/variant fields,
source case IDs, provisional variant ID, and target human casting ID/UUID.

The evidence reveals an important boundary that a name-only table hides. All four pairs clearly
refer to the same named casting family, but their releases are not automatically the same variant.
The 2015 green `'67 Chevy C10` human record differs from the 2025 HW Hot Trucks rows; the Purple
Passion human label says 2026/pink while the Wiki rows are 2025 HW Designed By; Tesla's human red
label lacks matching Wiki color evidence. Subaru BRZ shares a 2025/Zamac clue, but its human series
is Walmart Exclusive while the Wiki series is HW J-Imports.

### Code changes and why they were made

`build_fandom_priority_one_evidence.py` validates the T32 queue checksum and pending-state boundary,
requires exactly one human casting candidate per priority-1 family, rechecks normalized brand and
casting equality, and joins the family with `human_backed_catalog.json`. It retains both
`human_label_names` and `initial_names`; this matters because the initial text carries year or
listing context that a cleaned human label may omit.

The builder emits `priority-1-evidence.json`, a human-readable Markdown report, and a manifest that
freezes the queue, queue manifest, human catalog, and both outputs. It calculates only explicit
facts: source rows, release years, series sets, exact normalized family equality, and shared tokens
between the Wiki variant notes and human variant labels. It does not infer colors, dates, or release
identity from the prose.

Each packet contains two deliberately separate recommendations. The casting-family recommendation
is `merge_existing_family`, targeting the exact human casting. The variant recommendation is
`hold`, with `variant_identity_verified=false`. Reviewer confirmation fields remain empty, and the
family remains promotion-ineligible. Five tests freeze the four families, nine Wiki rows, exact
targets, retained evidence, Subaru `zamac` fact, family/variant boundary, hashes, and deterministic
regeneration.

### Technical choices, alternatives, and trade-offs

The evidence packet reuses frozen repository inputs rather than fetching four more web pages. The
purpose of this decision is to judge whether the two already-governed sources refer to the same
casting family; the exact names and recorded provenance are sufficient to pose that limited
question. Additional web research would be necessary for release/color promotion, which is
explicitly outside this packet.

The code reports shared variant tokens but does not turn them into a match score. A score would look
precise without a validated relationship to correctness. Showing `zamac` directly for Subaru is
more honest: it helps the reviewer understand why the release may be related, while differing
series labels and null Wiki color keep the variant held.

A single yes/no family question per packet was chosen instead of asking the user to interpret raw
UUIDs or decide every Wiki release at once. This keeps the immediate review small without weakening
the audit boundary. The trade-off is that even an accepted family merge will not increase the
canonical release count yet.

### Decision changes

The previous queue treated all evidence references as future reviewer work. T33 now pre-assembles
the repository evidence for priority 1 so the reviewer does not need to search across files. It
does not populate the reviewer's evidence field, because selecting which evidence justifies a
decision remains part of the reviewer-owned act.

The earlier shorthand “merge these four” is also narrowed to “recommend merging the casting family
only.” Variant identity remains held even for Subaru. This prevents a valid family conclusion from
silently granting invalid year/color/series equivalence.

### Verification evidence

Four packets cover nine unique Wiki source rows and exactly four human casting targets. Each target
passes exact normalized brand/casting equality, has retained human source cases and provisional
variant evidence, recommends a family-only merge, holds the variant, and remains pending and
promotion-ineligible. Only Subaru has a shared explicit variant token: `zamac`; its series sets are
not exact.

The packet checksum is
`4d6ede8ba1bbb3447f2d403885d4d68bb9d71893cbf012994b2be37e77ad8294`; the Markdown checksum is
`077d9b078514b8628b99244936f426652a46679f4e74642858c00c8067db98ab`.
The deterministic `--check` passed, five focused tests passed, and the complete host suite passed
94/94. T30–T32 checks, fixture validation, Python compilation, both Compose configurations, and
whitespace checks passed. No network request or database/runtime mutation occurred.

### Incomplete work, risks, and next step

No human decision has been recorded. The evidence packet uses stored labels and does not prove the
source listings themselves are still available. Exact family naming can support the proposed
family relationship but cannot establish individual release identities or resolve missing colors.

The next step is for the project owner to accept or reject the four family-only recommendations.
Acceptance means only “these Wiki rows and this human draft belong to the same named casting
family”; all nine release rows remain variant-held. Once the answers are given, a validator can
record reviewer/time/reason/evidence and update the queue without creating canonical database rows.

## 2026-09-08 — A 53-family queue makes human adjudication explicit

### What was executed and what problem it solves

T31 reduced 100 Wiki rows to 53 casting-family relationships, but its row-level JSON was still a
machine pre-review rather than a practical human workflow. T32 prepares the actual adjudication
queue. It groups every source row under one stable family-review ID, puts the four exact
human-catalog candidates first, places the remaining 49 research-required groups second, and emits
both a machine-readable queue and a Markdown worksheet that a non-programmer can inspect.

This solves two different risks. First, it prevents a reviewer from issuing the same casting
decision two or three times merely because one model has several release/color rows. Second, it
makes the absence of completed human review visible: all 53 decision objects are pending, their
reviewer fields are empty, and none is eligible for promotion or PostgreSQL ingestion.

### Code changes and why they were made

`build_fandom_adjudication_queue.py` validates the T31 report against its manifest, rejects
duplicate source IDs or rows that have already crossed the review boundary, groups by the frozen
normalized family key, unions exact candidate IDs, preserves every contributing toy/collector/
series/variant row, and assigns stable SHA-derived family-review IDs. Exact-candidate groups receive
priority 1; groups requiring source research receive priority 2.

The generated `adjudication-queue.json` defines a closed decision contract:
`merge_existing_family`, `create_new_casting`, `hold`, or `reject`. A completed decision must state
who decided it, when, why, and which evidence supports it. Creating a new casting additionally
requires independent source confirmation. `adjudication-queue.md` renders the same queue as two
plain tables, making the work accessible without editing or understanding the larger JSON files.

The queue manifest freezes both T31 input files plus the JSON and Markdown outputs. Build mode
writes all three outputs; `--check` rebuilds them in memory and rejects any byte difference. Five
tests verify complete one-time source coverage, stable unique family IDs, priority ordering, the
four exact human candidates, the closed decision contract, all-pending safety, hashes, and
determinism.

### Technical choices, alternatives, and trade-offs

The unit of human work is a casting family, not a Wiki row. This reduces the decision count from 100
to 53 while retaining nested release evidence. It does not merge the releases themselves: a family
decision can confirm that two sources discuss `Subaru BRZ`, but color, series, toy number, edition,
and rarity remain separate variant questions.

The queue is stored as JSON plus Markdown instead of adding a database admin UI. JSON provides a
strict future automation contract; Markdown gives the project owner a readable worksheet and clean
Git diff. A full UI could improve ergonomics later, but building authentication, concurrent edits,
and audit storage before validating the decision model would expand this Lite milestone without
improving identity evidence.

No entries were filled on behalf of the user. Although an AI can suggest that an exact name should
be reviewed for merge, recording that as `human verified` would create false provenance. Empty
reviewer fields are intentionally treated as meaningful safety state, not incomplete formatting.

### Decision changes

The prior next step was described broadly as human adjudication. Implementation clarified that the
project first needed an artifact a human could actually adjudicate. T32 therefore completes queue
preparation while leaving the substantive decisions open. This is a narrower claim, but it creates
a defensible separation between AI-assisted organization and human-owned labels.

The decision contract also changed from an informal request for a reason to a required four-part
audit record: reviewer, timestamp, reason, and evidence references. This makes future promotion
decisions reproducible and allows a validator to reject anonymous or unsupported approvals.

### Verification evidence

The queue contains 53 stable family IDs and nests all 100 unique source rows exactly once. Four
families are priority 1 and 49 are priority 2. Completed decisions and promotion-eligible families
are both zero. The queue checksum is
`638f35d36bbf25ec0767210c038e6ee3c1e097f4f3e67d78a9bbef4a8dd45558`; the worksheet checksum is
`748ce49c0c54afe0b60e2cc7d25275a990462f8116060f105059c4dc000acd36`.

The queue's deterministic `--check` passed, five focused tests passed, and the complete host suite
passed 89/89. Fixture validation, T30 staging validation, T31 review verification, Python
compilation, both Docker Compose configurations, and whitespace checks passed. The milestone made
no network request, database write, catalog mutation, or AI-evaluation change.

### Incomplete work, risks, and next step

Every substantive decision remains pending. The Markdown worksheet is readable but not a multi-user
approval interface, and the current builder deliberately refuses to infer human identity. A later
decision validator still needs to enforce target IDs for merges, evidence for new castings, and the
required audit fields before a promotion artifact can exist.

The next step now genuinely requires reviewer input, beginning with the four priority 1 families.
After those decisions are recorded, the 49 priority 2 names require independent source checking.
Only validated decisions—not the queue or pre-review suggestions—may feed future canonical and
PostgreSQL ingestion.

## 2026-09-07 — Cross-catalog review turns 100 Wiki rows into 53 review groups

### What was executed and what problem it solves

T30 produced a safe 100-row staging dataset, but a reviewer would still have needed to open three
large JSON files and compare every name manually. T31 builds the missing bridge: a deterministic
row-level report that checks each Wiki candidate against both the canonical fixture and the
human-backed draft, while preserving the rule that only a person may approve identity promotion.

The result also exposes why “100 imported rows” is not the same as “100 new car models.” Those rows
collapse to 53 distinct normalized casting families because many models have a base release and a
second-color or other variation. Nine rows, representing four families, already have an exact
human-backed family candidate. Ninety-one rows, representing 49 families, have no exact candidate
in either reviewed catalog. None exactly match the intentionally narrow synthetic canonical
fixture.

### Code changes and why they were made

`review_fandom_catalog_pilot.py` loads the frozen Wiki staging file, `catalog.json`, and
`human_backed_catalog.json`. It builds indexes on normalized brand plus casting and emits a review
record for every source row. Each result includes the input fields needed for review, normalized
family key, match reason, exact canonical/human candidate IDs, recommended review action, and three
remaining checks: confirm casting identity, classify release versus variant, and resolve color
without image inference.

The same command supports `--check`. In build mode it writes `review.json` and a manifest; in check
mode it regenerates both entirely in memory and requires byte-for-byte equality with the committed
files. The manifest hashes all three inputs and the output, so changing the Wiki snapshot or either
catalog makes the old review demonstrably stale instead of silently reusing it.

Five tests freeze row coverage, source order, status/family counts, the four current human-family
names, candidate boundaries, disabled unsafe matching options, all-hold decisions, checksums, and
determinism. README, attribution, MVP requirements, QA review, AI-eval exclusions, evidence, and the
decision log were updated so the report cannot be mistaken for model evaluation or database
ingestion.

### Technical choices, alternatives, and trade-offs

The matcher uses NFKD ASCII normalization, case folding, and alphanumeric tokens, then requires an
exact brand/casting key. This mirrors the project's conservative human-label alignment philosophy
and handles harmless punctuation differences such as curly apostrophes. It deliberately does not
use embedding similarity or fuzzy edit distance. Those methods could surface useful suggestions,
but without a verified threshold they could merge related yet distinct Skyline, Camaro, or model-
year castings and make a review shortcut look like ground truth.

Collector number was also rejected as a stand-alone identity key. In the Wiki data, multiple color
rows share collector numbers, and the canonical fixture uses a different synthetic scope. A number
match without matching source semantics would therefore be a coincidence, not sufficient identity
evidence.

Even exact human-family matches remain non-promoting. The human catalog itself is provisional, and
the Wiki row still lacks verified color. The report consequently chooses
`review_existing_human_family` as a recommended action while keeping canonical UUID/ID null. For
unmatched rows it says `review_possible_new_casting_family`, not “new casting,” because absence of
an exact match may be caused by spelling or coverage gaps.

### Decision changes

The previous next-step wording proposed a promote/merge/reject review of all 100 rows. Implementation
showed that automatic final decisions would overstate the available evidence. T31 therefore splits
review into two stages: deterministic pre-classification now, human adjudication later. This still
reduces the workload to 53 family groups and gives every decision an evidence trail, without
claiming that code can replace source-aware review.

This also changes the practical review order. The four exact human-family groups should be examined
first because they already have related human-labelled evidence. The 49 unmatched groups follow as
possible new families. Release/color classification remains separate within each family so a
second-color row cannot accidentally create a second casting.

### Verification evidence

The frozen report contains 100 rows across 53 families. Row counts are 9
`exact_human_casting_family` and 91 `no_exact_casting_family`; family counts are 4 and 49. The
matched families are `'67 Chevy C10`, `Purple Passion`, `Subaru BRZ`, and `Tesla Model S Plaid`.
All 100 decisions are `hold_for_human_review`, and canonical promotion count is zero.

The report checksum is
`720292870a04656df0a7a61ab7d649457990e09a19172b450f4557ad878f0c4e`. The `--check` regeneration
passed, five focused tests passed, and the complete host suite passed 84/84. Fixture validation,
Wiki staging validation, Python compilation, both Compose configurations, and patch whitespace
checks also passed. T31 made no network request and no PostgreSQL or runtime-catalog write.

### Incomplete work, risks, and next step

The report is machine pre-review, not human verification. Exact spelling does not prove that a
2025 release belongs to the same variant, and no exact spelling does not prove that a family is
new. Color remains unresolved for all 100 source rows. The human-backed catalog is itself a review
draft, so its four matches cannot grant canonical identity.

The next step is human adjudication beginning with those four matched family groups. Each group
needs a recorded merge/hold/reject decision and reasoning, followed by the 49 possible-new-family
groups. Only approved rows should feed a separate promotion artifact and PostgreSQL transaction;
the raw review JSON must never be ingested directly.

## 2026-09-07 — A governed 100-row Wiki pilot starts catalog expansion

### What was executed and what problem it solves

The project previously had two useful but deliberately limited sources: 120 synthetic/curated
canonical variants and 101 human-reviewed noisy names whose identities mostly remain provisional.
Neither source tests how a larger public catalog would enter the system. T30 introduces the first
external catalog intake without prematurely treating community data as canonical truth.

The Hot Wheels Wiki robots endpoint returned HTTP 403, so the work did not begin an HTML crawler or
try to bypass that response. A single identified MediaWiki site-information request was used to
confirm the API and its reported `CC-BY-SA` rights metadata. A second request retrieved the complete
2025 mainline list at frozen revision `790665`. Because the revision response contained the whole
table in roughly 93 KB, the pilot required no individual model-page or image requests.

### Code changes and why they were made

`fandom_ingestion.py` contains the bounded network adapter and pure table parser. The adapter uses a
fixed HTTPS API origin, URL-encoded parameters, an identifying User-Agent, a 30-second timeout, a
3 MB response ceiling, and strict response/license checks. The parser selects the first sortable
table, cleans Wiki and HTML presentation syntax, preserves source markers, and splits descriptions
such as “2nd Color - Zamac” into a separate variant note. It never reads the photo cell into the
normalized record.

`fetch_fandom_catalog_pilot.py` writes three artifacts: the raw revision, 100 normalized staging
records, and a checksum manifest. Its `--raw-input` mode can rebuild normalized output from the
frozen revision without another network call. This was added after the first fetch so parser fixes
or schema reviews do not create unnecessary requests or silently move to a newer Wiki revision.

`validate_fandom_catalog_pilot.py` enforces the accepted boundary: exactly 100 records and unique toy
numbers, sequential source rows, matching raw/normalized checksums, the expected license, null
colors, null canonical UUIDs, review-only status, and no copied `File:` reference in normalized
records. Parser tests cover Wiki links, HTML, templates, series values, color-variation suffixes,
determinism, limit errors, and insufficient table rows.

The source attribution README links the exact revision and contributor history, describes every
normalization change, and states that the source-derived files retain CC-BY-SA terms. The external
directory is excluded from the runtime Docker build: the repo retains review evidence, while the
shipping API cannot accidentally load the staging snapshot.

### Technical choices, alternatives, and trade-offs

The pilot uses one completed yearly list instead of walking thousands of casting pages. A yearly
table is closer to the required product-variant grain because it includes year, toy number,
collector number, series, and series position in one revision. It also sharply reduces load and
makes the exact source reproducible. The trade-off is that the table does not contain a trustworthy
text color field and some suffixes describe release variations without fully defining their color.

Unknown color therefore remains null. Inferring “green” or “red” from a photo filename would turn
presentation metadata into unreviewed product truth, while downloading the image would introduce a
different copyright boundary because Fandom explicitly warns that media need not share the Wiki
text license. This reduces immediate field completeness but prevents a much harder-to-detect data
quality and licensing failure.

The records were not appended to `data/catalog.json` and were not inserted into PostgreSQL. A Wiki
row is a release/variation candidate, not automatically a unique casting or a canonical identity.
The accepted architecture treats collection as reversible staging and promotion as a later human
decision. This preserves the existing resolver benchmark and prevents external knowledge from
leaking into test labels.

### Decision changes

The earlier plan described future catalog expansion at approximately 3,000 rows but had no accepted
source adapter or promotion boundary. That is now narrowed into two separate milestones: first
prove revision-frozen, attributed, review-only intake; only then define promotion and scale. The
project can now reproduce external extraction, but it still cannot claim a 220- or 3,000-row
canonical catalog.

The first generated parser counted the header chunk when assigning `source_row`, making the first
data record appear as row 2. Review caught that ambiguity before acceptance. The parser now numbers
valid data rows from 1, the raw revision remains unchanged, and normalized/checksum artifacts were
regenerated offline. This decision makes source-row references understandable without another API
request.

### Verification evidence

The accepted dataset is `fandom-hot-wheels-2025-pilot-r790665-v1`. It contains 100 records with 100
unique toy numbers, sequential rows 1–100, and 45 explicit variant notes. All 100 colors and
canonical UUIDs are null. The raw checksum is
`67521e8544de2dd15527e6d2234598c7c70a1e6d9e6597fde06c88bf95854510`; the normalized checksum is
`e5e0384afcf9fb2c7924a30fd9e308ea713a785be6e1d103bde54251cbd6b9a6`.

The dedicated frozen validator passed, the complete host suite passed 79/79, Python compilation
passed, and patch whitespace checks passed. No image file was downloaded. The checked-in raw and
normalized files total under 200 KB, and neither is part of the Docker runtime context.

### Incomplete work, risks, and next step

The 100 rows still need human review before promotion. The largest unresolved field is color, and
the identity policy must distinguish a new casting, an ordinary yearly release, a second color, a
store exclusive, Treasure Hunt, and Super Treasure Hunt. Assigning UUIDs before those rules exist
would produce durable but potentially wrong identities.

CC-BY-SA attribution/share-alike obligations apply to the source-derived directory, and this record
is not legal advice. The bounded importer has implementation safeguards but did not receive a formal
security or legal sign-off. It is intentionally a manual one-shot command, not recurring scraping.

The next step is to create a review/promotion artifact for these 100 rows: compare them with the
existing canonical and human-backed catalogs, classify exact casting-family matches versus new
families, and leave unresolved records unpromoted. Only after reviewing that report should the same
revision-frozen method fetch additional completed years toward 3,000 variants.

## 2026-09-07 — Exact pgvector completes the PostgreSQL canonical retrieval pair

### What was executed and what problem it solves

T09 moved canonical text candidate generation into PostgreSQL, but dense candidates still came from
vectors calculated and searched inside each API process. T10 now gives the same deterministic
catalog vectors a durable lifecycle: a command materializes them into PostgreSQL, startup proves
that the complete expected artifact is present, and each PostgreSQL-backed request performs exact
cosine-distance retrieval through pgvector. Canonical sparse and dense sources therefore share the
database boundary while the independent human-knowledge RAG remains non-canonical.

The change solves more than storage. Previously a database could be catalog-ready while containing
zero vector rows, and the API had no way to distinguish that incomplete state. It now refuses
readiness if dense metadata is missing, the catalog/model/text version differs, the artifact
checksum changes, or even one expected UUID/version/checksum row is absent.

### Code changes and why they were made

`embedding_artifacts.py` defines a stable catalog-text contract, composite embedding version,
pgvector literal encoding, per-product checksum, and whole-index checksum. These values are derived
from sorted canonical UUIDs so the artifact does not change merely because catalog file order
changes. The vector is included in each row checksum so a change to input text or deterministic
encoding output changes the recorded artifact.

`postgres_embeddings.py` adds the `pvr-materialize-embeddings` command. It first verifies the T07
canonical catalog, then writes every `vector(192)` row and the `canonical_dense` metadata row inside
one transaction. `ON CONFLICT` makes an identical rerun safe, while identities outside the loaded
catalog are rejected instead of silently deleted. A post-commit verification ensures the command
does not report success for an incomplete artifact.

`PostgresDenseRetriever` encodes the normalized query with the same versioned model and sends the
vector, version, and limit as SQLAlchemy-bound parameters to the existing exact `<=>` query. The
database returns UUIDs and cosine similarity scores; every UUID must map back to the checksum-matched
catalog. `ResolverService` now injects both PostgreSQL sparse and dense retrievers when that backend
is selected. Debug and health output report the actual dense implementation rather than a generic
configuration label.

Compose gained a separate `materialize` job after migration and ingestion. Keeping this step
separate makes data lifecycle failures visible and lets a future model upgrade rebuild vectors
without pretending it is ordinary catalog ingestion. Unit tests cover repeatability, content-driven
checksum changes, bound query parameters, limits, empty input, and unknown UUID failure. A dedicated
T10 verifier covers the real database and API boundary.

### Technical choices, alternatives, and trade-offs

The accepted Lite implementation deliberately materializes `hashing-v1` before introducing a
sentence-transformer. This model is local, deterministic, CPU-only, and already used by the verified
offline path. It lets the project test versioning, transactional materialization, readiness, and
pgvector querying without mixing those concerns with model downloads, licensing, caches, or a new
quality claim. It remains a lexical hashing baseline and is not described as neural semantic search.

Exact cosine search was retained instead of adding HNSW or IVFFlat. With 120 current rows—and the
planned first scale check near 3,000 rows—exact search provides deterministic complete comparison
and avoids index build/tuning/recall trade-offs that have not been justified by measurements. An
approximate index becomes a valid option only after observed latency or scale requires it.

The alternative of trusting only one metadata checksum was rejected. Startup compares the expected
identity, embedding version, and checksum for every row. This costs one deterministic catalog
encoding pass during startup, but catches incomplete or stale materializations instead of letting
the API operate on a silently partial dense index.

### Decision changes

T09 intentionally left PostgreSQL mode hybrid: database sparse retrieval plus in-memory dense
retrieval. That temporary boundary is now removed for the canonical catalog. In PostgreSQL mode,
both candidate sources execute in PostgreSQL; offline mode remains unchanged and requires no
database.

T10 originally requested a pinned local embedding artifact and was marked partial because only the
in-memory hashing implementation existed. Under the accepted Lite scope, the deterministic model
identifier, dimensions, catalog-text contract, vectors, and checksums now form the pinned artifact.
The task is complete for plumbing and exact retrieval, while the materially different claim of a
neural embedding model remains deferred and explicit.

### Verification evidence

The isolated `pvr-t10` environment used host PostgreSQL port `55435`, PostgreSQL 16.14, and the
rebuilt Python 3.12 project image. Migration and ingestion completed before 120/120 embeddings were
materialized with version `hashing-v1-d192-catalog-searchable-text-v1` and index checksum
`557d7153b077624f64cdc7bd2ada824df90a683216f7c67159e22a68f20d2464`. Repeating the command produced
the same logical rows and result.

Exact dense retrieval recovered a catalog alias and all 12 matched frozen-test targets within
Top-25, for Recall@25 `1.0`. Deleting one embedding row made a newly constructed API fail readiness
with 503; rerunning materialization restored the artifact. A real Uvicorn service on
`127.0.0.1:18010` reported both PostgreSQL sparse and exact dense dependencies ready and resolved
`2022 Chevy Nomad Red #101` to `hot-wheels-chevy-nomad-2022-mainline-red-101`. Its correct candidate
ranked first in sparse, dense, structured, and RRF sources. Separate frozen examples preserved all
three policy outcomes: `matched`, `ambiguous`, and `no_match`. The final host suite passed 77/77,
including rejection of an embedding dimension that does not match the `vector(192)` schema.

### Incomplete work, risks, and next step

No PostgreSQL latency benchmark was taken, so the earlier offline/container p95 numbers must not be
applied to this path. Startup recomputes expected deterministic vectors and checksums, which is
acceptable at 120 rows but should be measured near 3,000. Row checksums prove expected provenance
and version metadata; they do not independently hash PostgreSQL's stored float bytes. Runtime health
remains a startup snapshot, although a later database loss fails the next retrieval request with
503.

The next evidence-driven action is to expand the licensed/reviewed catalog toward approximately
3,000 variants and measure exact pgvector latency and retrieval quality. A neural embedding model
or approximate vector index should be selected only if that held-out evidence shows a real gain or
performance need. The remaining T14 external pointwise reranker is likewise not justified by the
current fixture, where the existing heuristic produced zero Top-1 gain over RRF.

## 2026-09-07 — PostgreSQL sparse retrieval enters the canonical RAG path

### What was executed and what problem it solves

T07 made the canonical catalog durable in PostgreSQL, but every API lookup still searched only the
JSON-backed in-memory index. T09 now lets an explicitly selected PostgreSQL backend retrieve
canonical sparse candidates from the installed `product_search` documents. The default offline
mode remains unchanged, while `PVR_BACKEND=postgres` is now a working, readiness-checked option
instead of an intentionally unavailable placeholder.

The observable result was verified over real HTTP. A PostgreSQL-backed API reported database
version `16.14`, sparse retriever `postgres-fts-simple-v1`, and ready health, then resolved
`2022 Chevy Nomad Red #101` to the expected canonical ID. The same database retriever recovered all
12 frozen matched test targets within Top-25 and returned an exact catalog identifier at Top-1.

### Code changes and why they were made

`retrieval.py` now defines `PostgresSparseRetriever` behind the same retriever protocol used by the
in-memory sparse implementation. It converts already normalized title tokens into a bound
`websearch_to_tsquery` value, executes the existing fixed SQL statement, and maps returned UUIDs to
typed `CatalogProduct` objects. Returning an unknown UUID is an error rather than silently accepting
a database/catalog mismatch.

`postgres_retrieval.py` owns SQLAlchemy engine execution and startup verification. It checks the
installed catalog version, full-content checksum, product count, and search-document count before a
service becomes ready. `service.py` selects only the sparse implementation according to
`PVR_BACKEND`; dense and structured retrieval, RRF, calibration, policy, and the independent human
knowledge source retain their existing contracts. Debug metadata identifies the actual sparse
version. `api.py` reports the database/index versions and maps a runtime retrieval dependency loss
to HTTP 503 rather than an internal-error 500.

Compose now passes the backend switch and database URL into the API service. Docker packages the
T09 verifier, while unit tests record the SQL statement and parameters without needing a database.
The README documents migration, ingestion, and the opt-in PostgreSQL API start order.

### Technical choices, alternatives, and trade-offs

The PostgreSQL path was introduced at one retrieval boundary rather than moving sparse, dense, and
structured logic together. This makes failures attributable and leaves T10's vector model/version
questions independent. It creates a temporary hybrid canonical path—PostgreSQL sparse plus
in-memory dense/structured—but avoids pretending that empty `product_embedding` rows are a working
pgvector system.

Normalized tokens are joined with web-search `OR` for candidate generation. An all-`AND` query
would let one irrelevant seller token remove the correct product entirely; candidate retrieval
instead favors recall, while RRF, calibration, and abstention control precision later. PostgreSQL's
built-in `ts_rank_cd` was retained rather than adding a BM25 extension, matching the Lite scope and
avoiding another deployment dependency before 3,000-row evidence exists.

All title content and limits remain SQLAlchemy-bound parameters. Only a fixed repository-owned SQL
constant is executed; raw titles are never interpolated into SQL or identifier names. This matters
even though `websearch_to_tsquery` is designed for user-style input, because SQL parameterization is
the actual boundary preventing a title from becoming executable database syntax.

### Decision changes

The earlier fail-closed decision rejected every `PVR_BACKEND=postgres` configuration because no
query adapter existed. That decision is narrowed: PostgreSQL mode is now accepted only after T07
metadata and row-count verification succeeds, and only canonical sparse retrieval moves to the
database. Missing/stale data still fails readiness. Exact dense pgvector retrieval remains deferred
and the ordinary default remains `offline`.

The project also previously described PostgreSQL as entirely outside the API runtime evidence.
That is no longer accurate for sparse retrieval: both in-process API and real container HTTP paths
passed. Existing latency numbers remain offline-only, so no PostgreSQL latency or concurrency claim
was added.

### Verification evidence

The final host suite passed 71/71, including two additional API fail-closed tests. The isolated
Compose project `pvr-t09` used port `55434`, migrated PostgreSQL 16.14, and ingested all 120 fixture
products. T09 verification reported identifier Top-1, 12/12 Recall@25 (`1.0`), a forced query plan
using `ix_product_search_document`, injection-shaped bound-input safety, API readiness, and checksum
mismatch health 503. A real Uvicorn container on `127.0.0.1:18009` returned the expected matched
canonical ID and PostgreSQL sparse version.

Unit tests additionally prove that query and limit values are parameters, SQL text never contains
the injection-shaped title, invalid limits are rejected, empty token sets avoid database work, and
unknown database UUIDs fail closed. Fixture validation, Python compilation, both default and
PostgreSQL-profile Compose configuration, and `git diff --check` also passed. All isolated T09
containers, network, and volume were removed.

### Incomplete work, risks, and next step

Startup verifies database consistency, but health does not yet actively re-query PostgreSQL on every
request; a database lost after startup is detected on retrieval and returned as 503. OR-based FTS
was measured only on 120 synthetic/curated products, and its ranking quality or latency may change
with 3,000 real variants. The FTS score is not BM25, dense retrieval remains in memory, and no
external Wiki catalog has been imported.

The single highest-value next action is **T10 — materialize versioned deterministic embeddings and
execute exact pgvector retrieval**. After both PostgreSQL candidate sources work, the project can
benchmark the complete database-backed canonical path before scaling the licensed catalog toward
3,000 records.

## 2026-09-06 — Atomic PostgreSQL canonical-catalog ingestion

### What was executed and what problem it solves

The PostgreSQL schema had already passed its migration lifecycle, but the running project still had
no implementation that could put catalog knowledge into those tables. T07 now installs a complete
validated catalog snapshot through the same ingestion contract used by the in-memory tests. This
closes the gap between “the database tables exist” and “the database contains a coherent catalog.”

On the first fixture import PostgreSQL received 120 product variants, 240 aliases, 120 identifiers,
120 provenance records, 120 sparse-search documents, and one catalog metadata record. Repeating the
same import left every stored row unchanged. A deliberately conflicting import modified an early
record before failing later, and the transaction restored the entire pre-import snapshot. A second
negative case omitted one existing product and was rejected rather than silently deleting its
canonical identity.

### Code changes and why they were made

`src/product_variant_resolver/postgres_ingestion.py` implements the existing `CatalogRepository`
contract with SQLAlchemy 2 parameterized statements. One connection and transaction span every
product plus the final metadata update. Parent product identity is checked by UUID, canonical slug,
and natural-key fingerprint; aliases are reconciled by normalized text; identifiers are checked for
ownership before update; provenance is replaced only when its complete ordered content changes;
and `product_search` receives deterministic source text plus PostgreSQL's `simple` `tsvector`.

`catalog.py` now preserves the structured alias and identifier type/source records that the prior
in-memory resolver flattened into strings. The flattened values remain for retrieval compatibility,
while PostgreSQL can retain `alias_type`, `identifier_type`, and source provenance. Its checksum now
covers the complete normalized catalog representation instead of UUID/slug alone, because a casting,
series, alias, or provenance correction must produce observable version evidence.

The installed `pvr-ingest` command and Compose `ingest` service provide one documented operator
path. Docker includes the isolated verification runner, while `.dockerignore` permits only that
specific additional script. The API backend was deliberately not switched to PostgreSQL: writing
catalog rows is T07, whereas querying FTS and pgvector safely belongs to T09/T10.

### Technical choices, alternatives, and trade-offs

Atomic full-snapshot ingestion was chosen over per-product commits and truncate/reload. Per-product
commits could leave the database half-updated after record 2,500 of a future 3,000-row import.
Truncation would temporarily remove all identities and recreate unchanged surrogate rows. The
selected reconciliation keeps unchanged rows and timestamps stable but still makes all changes
commit together.

The importer also refuses to infer deletion from omission. This is intentionally conservative for
future external sources: a disappeared Wiki row could mean a parsing or export problem rather than
a retired Hot Wheels release. The cost is that genuine retirement will require a later explicit
active/retired field and policy. `product_embedding` remains empty because inserting placeholder
vectors would make T10 look complete without a versioned embedding model or checksum.

### Decision changes

T07 was previously marked partial because only `InMemoryCatalogRepository` implemented the
transaction contract. It is now complete for the 120-product Lite fixture and real PostgreSQL 16
runtime. PostgreSQL is still not the API resolver backend: this milestone promotes database
persistence only, not database retrieval, latency, or 3,000-record external-catalog readiness.

The first checksum implementation tracked only UUID and slug. That was sufficient to recognize an
identity list but would miss corrected searchable fields. The checksum was expanded before accepting
T07 so metadata changes whenever relevant catalog content changes. Structured alias/identifier
records were preserved for the same reason: source and type are database facts, not disposable
loading details.

### Verification evidence

The isolated Compose project `pvr-t07` used host port `55433` and a dedicated named volume. Alembic
upgraded an empty PostgreSQL 16/pgvector database to revision `0001`. The production repository then
passed first import, exact repeated-row comparison, mid-import canonical-ID collision rollback, and
incomplete-snapshot refusal. Counts were 120 products, 240 aliases, 120 identifiers, 120 provenance
rows, 120 search documents, one metadata row, and zero embeddings by design.

The first verification attempt exposed a string-versus-`Path` mismatch in the verification
entrypoint before any write occurred. Explicit environment-boundary conversion fixed it; the rebuilt
image passed the complete scenario and the strengthened missing-row scenario. The host suite passed
66/66 before documentation finalization, fixture checksum validation passed, Python compilation and
Compose configuration passed, and the isolated containers, network, and volume were removed.

### Incomplete work, risks, and next step

The importer expects a migrated PostgreSQL database and a complete validated canonical snapshot. It
does not crawl Fandom, create provisional identities, review licensing, materialize embeddings, or
query PostgreSQL during `/resolve`. It also does not yet model retired products, so intentional
deletion is refused. The local Compose password is development-only and must not be reused outside
the loopback development environment.

The single highest-value next action is **T09 — PostgreSQL sparse retrieval**. That task will query
the populated `product_search` GIN index with bound parameters and prove that identifiers and rare
casting terms recover the correct canonical candidates before pgvector is added.

## 2026-09-06 — Human-backed catalog connected as the second RAG source

### What was executed and what problem it solves

The human-backed catalog previously existed only as a checked-in draft. This iteration connected it
to the running resolver so the project now searches two distinct knowledge corpora for every title.
The original canonical catalog path still owns final identity and abstention. The new human
knowledge path searches reviewed real-world names and exposes provisional suggestions that explain
what the system has seen before, especially when the small fixture catalog cannot return a product.

For the smoke query `Hot Wheels BMW M3 GT2 Neon Speeders`, the human path ranks the reviewed BMW M3
GT2 record first, but the final response remains `no_match` with null UUID because no canonical BMW
exists in the fixture catalog. This is the intended safety boundary: the second RAG source improves
knowledge retrieval without changing a draft label into a production identity.

### Code changes and why they were made

`src/product_variant_resolver/human_knowledge.py` adds a strict loader and an independent hybrid
retriever over the 100 provisional variants. Sparse scoring uses IDF-weighted token overlap so rare
model tokens contribute more than common words. Dense scoring reuses the deterministic `hashing-v1`
embedding already shipped by the Lite runtime, and RRF combines the two ranks without directly
adding incomparable scores. A shared-token gate prevents the non-semantic hashing baseline from
returning candidates for wholly unrelated input.

`ResolverService` loads both catalogs, runs `human_knowledge_retrieval` after shared signal
extraction, records a separate timing/span and candidate count, and includes bounded human results
only in debug payloads. The canonical candidate list alone continues into reranking, calibration,
policy, and final product selection. `schemas.py` therefore gives human candidates explicitly
provisional fields instead of reusing `CandidateDebug`, which would incorrectly imply canonical
identity. `config.py`, `.env.example`, Dockerfile, and `/health` expose the new required catalog and
index versions; a missing human catalog makes readiness fail rather than silently claiming Dual RAG.

The debug UI now renders a separate Reviewed-name candidates table with a visible warning that the
rows are retrieval evidence only. Human names and even markup-like text are assigned through
`textContent`, preserving the existing untrusted-input boundary. Default API responses remain
unchanged and continue to omit all debug data.

### Technical choices, alternatives, and trade-offs

The new source deliberately does not merge its provisional records into the canonical catalog and
does not override `no_match`. Merging would make the existing calibrator and thresholds operate on a
different identity space without training evidence. Allowing a human hit to override policy would
produce apparent coverage immediately, but would erase the distinction between a reviewed name and
a fully specified canonical variant.

Running the second retrieval on every request makes the Dual RAG execution boundary observable and
keeps timing evidence honest. The trade-off is additional CPU work even when debug is false; the
catalog currently has only 100 provisional variants, so Lite mode accepts that cost while deferring
performance optimization until a measured bottleneck exists. The output is shown only in debug to
preserve the minimal consumer contract.

No Top-1 or Recall@K claim is made for the new path. Its indexed aliases come from the same source
cases, so evaluating those aliases against the index would measure memorization. A defensible metric
requires a separate grouped holdout or independently written noisy queries. The next task should
create that evaluation set or define the review-to-canonical promotion workflow before human
evidence influences final decisions.

### Verification evidence

The focused backend, API, observability, and UI selection passed 25/25 tests after adding an explicit
loader test that rejects any provisional variant whose status bypasses canonical review. The full
host suite then passed **64/64**. `scripts/validate_fixture_data.py` reproduced manifest SHA-256
`a4c851228939b3d12db7c879ce9c81e4ae008fd19d1032adb376b833e23c31b8`; Python compilation and
`git diff --check` both passed.

The integration evidence exercises the important product boundary, not only internal functions.
`Hot Wheels BMW M3 GT2 Neon Speeders` retrieves `BMW M3 GT2` / `Neon Speeders` first from the human
source while the API remains `no_match` with a null canonical identity. A known fixture query still
resolves through the canonical source, and default responses omit debug evidence. Health metadata
reports both human catalog and human retrieval-index versions. A missing human catalog prevents app
readiness rather than silently falling back to a single-source system.

These checks use the deterministic 100-document Lite catalog and `hashing-v1`; they do not establish
semantic quality on unseen marketplace titles, production latency under load, or a neural embedding
benchmark. The existing Starlette TestClient deprecation warning remains visible and non-failing in
the host environment. The single highest-value next action is an independently authored, casting-
grouped holdout evaluation so retrieval quality can be measured without testing the index against
its own aliases.

## 2026-09-06 — Human-backed casting catalog and provisional variants

### What was executed and what problem it solves

The conservative alignment proved that the 10-family synthetic fixture catalog cannot represent
the 97 real castings in the reviewed dataset. This iteration therefore built a separate
`human-backed-catalog-v1` instead of weakening alignment rules or overwriting the synthetic fixture.
All 101 confirmed source records are now organized into 97 casting entities and 100 provisional
variant groups that can support retrieval and a future human-review workflow.

The count difference is intentional. Three `83 Chevy Silverado` records remain three variants
because their labels distinguish blue, black, and baby-blue versions. Two `Toyota Supra` records
remain separate because one is Hot Wheels XL/Greddy and the other is Mainline/Fast & Furious. Two
`1970 Chevrolet Chevelle SS` records share the same normalized Premium/Fast and Furious structure,
so they become one provisional variant while retaining both case IDs, names, and pricing keywords.

### Code and data changes, with reasons

`scripts/build_human_backed_catalog.py` creates `data/human_backed_catalog.json` and its checksum
manifest. A casting key uses exact normalized brand and casting. A provisional variant key adds the
reviewed series and variant labels. Both levels receive deterministic UUIDv5 and readable IDs so
regeneration does not change references, while every variant remains explicitly
`needs_canonical_review`.

The catalog keeps all human names, pricing keywords, available initial names, failure categories,
and source case IDs. It does not parse missing year, collector number, scale, color, or edition from
free text. Those values may appear inside a human name, but automatically promoting them into typed
identity fields would mix interpretation with verified evidence and could make later corrections
silently remint an identity.

Focused QA initially exposed inconsistent brand display casing: the reviewed source contains both
`Hot wheels` and `Hot Wheels`, so choosing one complete spelling by frequency produced `Hot wheels`
throughout the draft. The builder now derives a stable display form from the already normalized
brand tokens, producing `Hot Wheels`, `Matchbox`, and `M2` consistently while retaining the original
human strings inside name aliases. This changes presentation only; grouping keys and stable UUIDs
remain based on the same normalized identity.

`scripts/validate_fixture_data.py` now checks the new catalog checksum against the human dataset,
count agreement, unique casting and provisional-variant identifiers, exact one-time coverage of all
101 cases, and mandatory canonical-review status. Seven focused tests cover deterministic output,
the 97/100/101 accounting, exact duplicate preservation, ID uniqueness, evaluation exclusions, and
non-merging of similar-but-distinct names. R19 and T28 record the behavior; README, decision D10,
QA, and AI-eval evidence explain why this catalog is retrieval-ready but not canonical truth.

### Technical choice and next decision

A two-level casting/variant draft was chosen over either extreme of creating 101 unrelated products
or collapsing every record with the same casting into one product. It preserves known structure
and repeated evidence without claiming that incomplete variant labels are production identifiers.
The trade-off is an additional review state and a second catalog artifact, but this boundary makes
future promotion auditable.

The next step is to connect this draft as a second, explicitly non-canonical retrieval source in the
Dual RAG pipeline. Results from that source must be presented as candidate knowledge or review
suggestions until typed attributes are verified and a promotion process mints final canonical IDs.

### Verification evidence

The builder produced 97 castings and 100 provisional variants from all 101 source records, and the
manifest recorded one merged duplicate source record. The central fixture validator passed. Seven
focused catalog tests passed, the complete host suite passed 57/57 with `PYTHONPATH=src`, Python
compilation passed, and `git diff --check` reported no whitespace errors. The already documented
host TestClient deprecation warning remained non-failing and is unrelated to this data-only runtime
boundary.

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

## 2026-09-12 — T48.4 frozen Human Knowledge RAG v2 evaluation

### Context, problem, and observable outcome

T47 had proved that all 42 accepted family documents were wired into the second, non-canonical RAG
source, but its exact-name smoke queries could not answer the important question: can the retriever
recover a family from independently worded marketplace-like text? T48.1–T48.3 therefore froze a
separate 105-case, project-owner-approved benchmark before any candidate output was inspected.
T48.4 has now run that first scored evaluation without changing the frozen query text, labels,
retriever, catalog, RRF settings, or thresholds.

The observable result is an honest **FAIL**: eight of nine precommitted gates passed, while
lexical-variation Recall@5 reached `31/42 = 73.81%`, one retrieved case short of the required 75%.
Overall positive Recall@5 was `73/84 = 86.90%`, Recall@1 was `58/84 = 69.05%`, MRR@5 was
`65.0/84 = 77.38%`, and family coverage was `42/42 = 100%`. Marketplace-noise cases, all four
merge controls, all forbidden-family checks, and all ten unrelated controls passed. This means the
system handles seller/year/condition wrappers well, but its harder typo, abbreviation, punctuation,
and spacing behavior is not yet consistent enough to clear the frozen family-quality gate.

### Implementation trace

`src/product_variant_resolver/human_knowledge_evaluation.py` is the new read-only scoring boundary.
It verifies the benchmark and manifest hashes, every referenced input checksum, exact 105-case
composition, and the frozen source/model/index settings before constructing the existing 142-
document Human Knowledge retriever. Within each case it retrieves and serializes the Top-5
candidates before reading the `expected` label branch. It then records typed IDs, UUIDs, sparse,
dense, and RRF ranks/scores, matched tokens, expected rank, forbidden-hit ranks, and an explicit
error category. Aggregate numerators and denominators are derived only from this ordered case array;
the validator independently recomputes them before accepting the report.

`scripts/generate_family_retrieval_report.py` converts the validated JSON into the compact human-
readable report at `reports/family-retrieval-v1/evaluation.md`. It deliberately refuses to render
metrics that differ from the raw-case recomputation, shows every failed case, links the AI-eval
record, and offers a non-mutating `--check` mode. JSON and Markdown writes use temporary files plus
atomic replacement so an invalid or interrupted evaluation cannot overwrite known-good evidence.

`tests/evaluation/test_human_knowledge_evaluation.py` covers metric formulas, preserved FAIL
behavior, all evaluator failure categories, a guarded mapping that raises if `expected` is touched
before retrieval, stale-input no-overwrite behavior, the actual frozen result, and byte-identical
JSON/Markdown reproduction. `docs/evidence/ai-evals/family-retrieval-holdout-v1.md` applies the
project AI-output rubric to the measured result and narrows the allowed claim. No API, canonical
ranking, confidence policy, PostgreSQL schema/data, benchmark source, or existing retriever code was
modified.

### Technical choices, alternatives, and trade-offs

The evaluator stores full raw candidates rather than only final percentages because a number such
as 86.90% cannot show whether errors come from empty retrieval, ranking beyond K, a wrong identity
type, or a safety-control violation. The larger JSON artifact is an accepted trade-off: it enables
every result and metric to be audited and regenerated without rerunning or trusting prose. The
Markdown report contains only a compact failure table while the JSON retains all 105 cases.

The existing sparse plus deterministic feature-hashing and RRF stack was evaluated unchanged.
Adding fuzzy matching, query expansion, a neural embedding, or a wider candidate limit could likely
improve the 11 lexical misses, but doing so after seeing this test set would convert an independent
holdout into a tuning set. The selected method therefore preserves the failed gate and requires a
new v2 holdout for final evidence after any redesign. The evaluation also records the
`signals.extract_signals-v1` source checksum in its output: token cleanup participates in the actual
runtime query path, even though the earlier frozen manifest separately named the normalizer and
retriever sources.

### Decision changes

Before T48.4, independent family retrieval quality was explicitly “not evaluated”; only exact-name
wiring, type safety, and canonical isolation had passed. That status now changes to a measured
**FAIL** for the current independent family-quality gate. The earlier T47 wiring/safety result
remains valid, but it cannot be used as a retrieval-quality claim.

Because the acceptance boundary says every gate must pass, the strong overall Recall@5 and perfect
control results do not cancel the lexical-style failure. T49 PostgreSQL/pgvector scale design and
the approximately 3,000-row expansion are therefore not authorized by this result. The next product
decision must be a retrieval redesign with separate development data, followed by a newly authored
unseen holdout; it must not lower the v1 gate or rewrite the failed queries.

### Verification evidence

The formal artifacts are `reports/family-retrieval-v1/evaluation.json` and `evaluation.md`, tied to
benchmark SHA-256 `440246fb6a3b38f56fc25c1ec939d53d6cfc4457fed738aad561899325808afd`.
Their raw counts are 73/84 Top-5 hits, 58/84 Top-1 hits, reciprocal-rank sum 65.0, 42/42 family
coverage, 31/42 lexical hits, 42/42 marketplace-noise hits, 4/4 merge hits, zero forbidden family
candidates, and 0/10 unrelated non-empty results. Error accounting contains ten
`expected_identity_not_retrieved`, one `no_candidates`, and 94 `none`, totaling all 105 cases.

The focused T48.4 suite reported **7/7 PASS**. Targeted Ruff reported no findings, and isolated
strict mypy (`--follow-imports=skip`) reported no issues in the three new source/test files. The
JSON and Markdown `--check` paths reproduced the checked-in bytes. Complete repository regression,
data-chain checks, canonical fixture metrics, Compose validation, and final scope review remain the
explicit work of T48.5 and are not claimed by this entry.

### Incomplete work, risks, and next step

The 105 queries are synthetic rather than live marketplace traffic, and 42 family groups produce
wide percentage steps: one additional lexical hit would have met the minimum. They test casting-
family retrieval, not release-variant identity, canonical resolution, confidence calibration,
database scale, concurrency, or production latency. After this publication v1 is development-known
and cannot serve as an unseen final test for a modified retriever.

The immediate next step is **T48.5 — close the Lite evaluation gate**: run the full suite and frozen
data chain, verify canonical/T47 regressions, compilation, Compose configuration, repository scope,
and report reproducibility, then write the final review/evidence mapping. If those engineering checks
pass, T48 will close with a truthful quality FAIL and a documented redesign requirement—not with
permission to begin T49.

## 2026-09-12 — T48.5 Lite evaluation-gate closure

### Context, problem, and observable outcome

T48.4 produced a valid model-quality FAIL, but that result alone did not prove that the evaluator
was reproducible in the complete repository, that canonical behavior stayed unchanged, or that the
earlier human/Fandom evidence chain still validated. T48.5 therefore performed the final Lite QA
closure. It did not attempt to improve retrieval or reinterpret the failed threshold.

The outcome has two deliberately separate verdicts. Engineering verification is **PASS**: 201/201
tests, the full deterministic data chain, fresh canonical evaluation, T47 regressions, compilation,
JavaScript syntax, both Compose configurations, and repository-scope checks succeed. Retrieval
quality remains **FAIL** because lexical-variation Recall@5 is still `31/42 = 0.7381` against the
precommitted `>=0.75` gate. As a consequence, T48 is complete but T49 and the approximately
3,000-row PostgreSQL expansion are not authorized.

### Implementation trace

No product code, retriever, runtime configuration, catalog, benchmark, policy, migration, or
PostgreSQL file changed in T48.5. `specs/family-retrieval-evaluation/review.md` now maps all sixteen
requirements to executable or immutable evidence and makes the two-verdict distinction explicit.
`docs/evidence/family-retrieval-evaluation-t48.md` records the artifact hashes, raw metric counts,
full verification chain, protected-file comparison, limitations, and carry-forward decision.

The T48 requirements/design/tasks headers were advanced from build/in-progress to verified and
complete, with both T48.5 tasks checked. README and the evaluation-directory README no longer say
that scoring has not happened; they now link the reports, state the failed lexical result, and warn
that T49 is blocked. The AI-eval gained final regression evidence, while decision D36 records why
the result must not be rounded, weakened, edited, or immediately retested with a changed model.
The shared AI-output rubric index now links this scored record instead of saying independent family
quality is still unevaluated.

### Technical choices, alternatives, and trade-offs

The closure treats “did we implement and verify the evaluation correctly?” separately from “did
the retriever meet the quality bar?” This avoids two misleading outcomes: marking sound evaluation
software as broken because it discovered a model weakness, or calling the model acceptable because
the software tests passed. The accepted trade-off is a completed milestone whose headline model
verdict is FAIL; that is more useful and defensible than a cosmetically green but altered gate.

The full source chain was replayed through non-mutating check modes rather than rebuilding committed
files in place. That choice protects frozen byte identities while still proving reproducibility.
Canonical regression used a new report under an isolated temporary directory so variable local
latency samples could not overwrite checked-in evidence. Compose was parsed in both offline and
PostgreSQL profiles, but containers were not rebuilt or load-tested because T48 changes no runtime
image or database path and makes no Docker/database performance claim.

Whole-repository Ruff and MyPy were run for transparency after the project dev tools became
available. Ruff 0.16.7 reports 143 existing style findings and strict MyPy reports 817 existing
findings, including unavailable optional dependencies and legacy test annotations. Automatically
rewriting the entire repository during an evaluation closure was rejected: it would create a large,
unrelated refactor and could alter frozen source checksums. The three T48.4 evaluator/report/test
files pass targeted Ruff and isolated strict MyPy, and the full executable suite remains green.

### Decision changes

Before T48, PostgreSQL scale design was conditionally next if the independent family-retrieval gate
passed. The condition is now resolved negatively. T49 changes from “available after evaluation” to
**blocked pending a redesigned retriever and a new unseen holdout**. The current family source may
remain as debug/review evidence because all safety and canonical-isolation checks pass, but it may
not become canonical, persistent, or production-claimed.

The proposed improvement direction is intentionally not selected here. Fuzzy/character candidate
generation, field-aware ranking, query expansion, or a neural representation may address different
parts of the eleven lexical misses, but choosing among them using the final v1 outcomes would blur
development and test evidence. A new feature spec must define development data and architecture;
final evaluation then needs a separately authored and owner-approved v2 holdout.

### Verification evidence

The complete Python suite reported **201/201 PASS**. Its sole warning is the known Starlette
TestClient use of an AnyIO alias deprecated by the locally resolved dependency version; no T48 code
emits it. The deterministic checks passed from fixture and 100-row pilot through review, base queue,
priority-one evidence/decisions, all five priority-two research/decision batches, the 42/4/7 registry,
the 42-document projection, the T48 query pack, owner decisions, benchmark, JSON evaluation, and
Markdown report.

A fresh 21-case canonical fixture report retained Recall@10/25/50, Top-1, MRR@10, hard-negative
accuracy, and precision at `1.0`, false-match rate `0.0`, and coverage `0.8333`. Its local macOS
arm64/Python 3.12.13 warmed p95 values were `2.3194 ms` for the direct pipeline and `2.6189 ms` for
in-process ASGI; these exclude containers, TCP, database, concurrency, and production. T47 tests
retain the 142-document typed index, exact-name family wiring, BMW variant behavior, and Proton Saga
canonical isolation.

Python `compileall`, `node --check ui/app.js`, default and PostgreSQL-profile `docker compose config
--quiet`, and `git diff --check` passed. Diff inspection from pre-implementation T48 baseline
`b7f6ac1` found no changes to protected canonical/runtime/policy/PostgreSQL files. The first attempt
to inspect the fresh canonical JSON assumed an obsolete flat output path; generation had succeeded,
and reading the emitted versioned path immediately confirmed the expected metrics. No committed
file or result was affected by that command-path mistake.

### Incomplete work, risks, and next step

The v1 test is synthetic, family-level, and only 42 groups wide; it does not represent marketplace
frequency, release variants, canonical accuracy beyond the unchanged fixture, PostgreSQL scale,
concurrency, or production latency. It is now development-known. Full-repository Ruff/MyPy debt and
the dependency warning remain separate maintenance items, not resolved within this evaluation
milestone.

The single highest-value next action is to **write a new retriever-redesign specification** that
defines independent development data and chooses how to address token-disruption failures without
tuning against v1. After implementation, a newly authored `family-retrieval-holdout-v2` must pass
before T49 persistence or the approximately 3,000-row expansion can resume.

## 2026-09-12 — Human Knowledge retriever-redesign Lite specification

### Context, problem, and observable outcome

T48 closed correctly but did not permit the planned PostgreSQL scale step: Human Knowledge RAG v2
missed the lexical-variation gate at 31/42. The failures share an architectural cause. V2 requires
at least one exact normalized token before a document is eligible, then computes the existing
feature-hashing dense score only inside that eligible set. A misspelled single-token identity cannot
reach the dense stage, while queries retaining only generic words can rank broad provisional-
variant documents instead of the intended family.

This planning step creates the complete Lite specification for a redesign, not a patch selected
from the failed test cases. `specs/human-knowledge-retriever-redesign/` now defines twenty testable
requirements, a concrete architecture and data lifecycle, and six ordered tasks. The observable
repository state remains unchanged at runtime: v2 is still active, T49 remains blocked, and no new
development query, v3 candidate, model artifact, or holdout result exists until the owner confirms
the spec.

### Implementation trace

`requirements.md` turns the redesign boundary into EARS-style behavior. It prohibits v1 use for
selection, requires an exactly 199-case development-only pack, restricts character fields by
document type, defines deterministic character indexing/union/fusion, freezes a 21-configuration
grid and safety-first selection rule, preserves API/canonical/failure safety, adds bounded local and
synthetic-3,000-document cost checks, and requires v3 to be committed before a new 105-case holdout
v2 is authored and owner-approved.

`design.md` specifies how character bigram/trigram TF-IDF postings operate on spaced and compact
identity forms and query windows. Token-sparse candidates and threshold-qualified character
candidates form a union; `hashing-v1` dense ranking is calculated only on that bounded union; sparse,
dense, and character ranks then enter weighted RRF without fabricated ranks for missing sources.
It also defines the development report, immutable selection artifact, optional debug fields,
readiness failure, v2 evaluation lifecycle, privacy boundary, test strategy, alternatives, 10x
behavior, and likely threshold conflict.

`tasks.md` divides delivery into six auditable handoffs: freeze development data, implement the
experimental v3/API/UI path, select and freeze one config or stop, freeze a new output-blind final
query pack, obtain owner labels and evaluate once, then close QA and decide T49. The tasks contain an
owner confirmation now and another mandatory owner gate before final labels/retrieval. Decision D37,
the specification evidence, and README record the same boundary for future reviewers.

### Technical choices, alternatives, and trade-offs

Character n-gram TF-IDF was selected as the proposed first redesign because the diagnosed problem
is identity spelling/spacing rather than general semantic question answering. It is dependency-free,
offline, deterministic, explainable by scored grams, and can use inverted postings for the later
roughly 3,000-document scale. The cost is a third retrieval score, an immutable selection artifact,
and additional API/debug evidence. It is still search/IR, not a neural embedding, and the
documentation says so explicitly.

Running current hash vectors across every document would require less code, but collisions and
generic fragments would enter without an interpretable floor. Edit-distance query rewriting can
silently force an unknown word toward a known identity. Fixed family quotas could improve the
reported metric without improving relevance and could hide valid variant merges. A sentence-
transformer could add semantic power but also model downloads, cache/version/license management,
startup memory, offline packaging, and a larger evaluation surface. Lite mode therefore tests the
deterministic candidate generator first and requires a new design if it cannot qualify.

### Decision changes

The prior closure named several possible techniques but intentionally chose none. D37 now proposes
one implementation path and, just as importantly, a selection method that cannot read the v1
benchmark. The new development set is allowed to be label-derived and therefore explicitly cannot
support final accuracy. It selects only a score floor and character RRF weight from a fixed grid;
all other retrieval parameters remain constant.

T49 remains blocked rather than renumbered or bypassed. A development winner merely freezes an
experimental v3. Final permission still requires new queries authored after that freeze, explicit
owner label approval, unchanged final gates, one scored v2 report, canonical/T47/T48 regression,
and full QA.

### Verification evidence

This is a documentation-only specification milestone. File inspection tied each proposed runtime
change to the current `HumanKnowledgeRetriever`, typed schemas, service serialization, debug UI,
evaluation lifecycle, and T48 failure evidence. The 11 v1 misses were inspected by expected family,
query, returned type/ID, and matched tokens to verify the shared-token/generic-token diagnosis; no
v1 metric, query, rank, or threshold was changed or used to select a configuration.

The spec contains HRR-R1–HRR-R20, six tasks with requirement back-references and acceptance
criteria, Overview/Architecture/Interfaces/Data Models/Error Handling/Security/Testing/Alternatives,
an explicit 10x assessment, most-likely-failure analysis, and two owner gates. `git diff --check` and
repository-scope inspection are the appropriate executable checks for this planning-only change;
no product test result is newly claimed.

### Incomplete work, risks, and next step

No evidence yet shows that character TF-IDF can satisfy recall and safety simultaneously. The exact
development queries do not exist, no configuration has been executed, no v3 artifact is frozen,
and the synthetic 3,000-document budget is only a proposed gate. Neural retrieval remains deferred,
and PostgreSQL persistence remains out of scope.

The immediate next action requires project-owner confirmation of the three spec files. After that,
HRR-T1 may create and freeze the 199-case development-only pack before any v3 configuration output
is generated. If the owner changes the architecture, counts, grid, or gate policy, the specification
must be revised before implementation rather than inferred during build.

## 2026-09-12 — HRR-T1 development-only challenge-pack freeze

### Context, problem, and observable outcome

The retriever-redesign specification could not safely proceed directly to character-search code.
Doing so would allow queries and configuration boundaries to be changed after seeing which settings
looked best—the same kind of test-set tuning that the project prohibited after the v1 holdout became
known. HRR-T1 therefore creates and freezes the development evidence before any v3 candidate is
executed.

The observable result is a new 199-case `family-retrieval-development-v1` pack: 168 positive cases
cover all 42 accepted families four times, 4 controls preserve existing-family merges, 7 controls
preserve held identities, and 20 unrelated controls divide evenly between opaque zero-overlap and
generic marketplace text. The pack and manifest both state that the questions are development-only,
derived from indexed/governance identities, and ineligible for final accuracy. No retriever output,
configuration result, selected winner, or v3 runtime artifact exists at this point.

### Implementation trace

`scripts/build_family_retrieval_development.py` adds a deterministic author/validator instead of a
manually editable JSON fixture. It validates the frozen review-family registry and projection, the
human-backed catalog used by merge targets, all source manifests, and exact 42/4/7/97 source counts.
The historical v1 query pack is opened only to reject exact or normalization-equivalent text; its
labels, candidates, ranks, metrics, and failures never become builder inputs.

The positive-case generator changes the identity in four distinct ways: one deleted character,
spacing/token-boundary disruption, abbreviation or numeric variation, and an exact identity inside
seller context. Merge and hold identities receive new development-only wrappers. Ten meaningless
opaque strings must share no searchable token with either Human Knowledge corpus, while ten generic
listings may use marketplace vocabulary but must contain no known casting phrase. Derived expected
targets come from the already approved registry relationships rather than new variant judgments.

The generated `development-pack.json` freezes cases and the 21-option grid before experimentation.
Its companion manifest hashes the pack, builder, six primary source/integrity files, and the v1
query pack plus manifest used for non-reuse checks. The script validates the complete prospective
result before opening output files and writes with temporary-file replacement, so invalid input
cannot erase the last valid freeze. `tests/test_family_retrieval_development.py` turns the dataset
boundary into ten executable contract tests. The feature requirements/design status now reflects
owner confirmation, HRR-T1 is checked in the task list, README links the evidence, and
`docs/evidence/family-retrieval-development-v1.md` gives the complete human-readable audit.

### Technical choices, alternatives, and trade-offs

Deterministic transformations were chosen over asking an LLM to generate 168 questions because the
exact operation on each identity remains inspectable and byte-reproducible, does not require an
external model/version, and cannot drift between runs. The trade-off is deliberate artificiality:
this pack measures whether implementation and a small fixed configuration family can handle known
spelling/token disruptions; it does not estimate real-user accuracy. That is why final evaluation
still needs a later output-blind, owner-reviewed holdout v2.

The grid is frozen as the specification requires: seven character floors from `0.25` through
`0.55` crossed with weights `0.5`, `1.0`, and `1.5`. Keeping sparse/dense weights, dimensions,
RRF `k`, and K fixed constrains degrees of freedom and makes a 21-result report understandable.
Safety gates are evaluated before quality and tie-breaking. This may legitimately yield no winner;
the accepted cost of fail-closed selection is preferable to widening the search after viewing
results.

Labels are stored in the development cases because selection needs them, but the artifact carries
an explicit leakage disclosure and prohibited-use list. A fully independent development corpus
would give stronger generalization evidence, but no separate owner-labeled corpus of sufficient
coverage exists. The future holdout—not this derived pack—will provide the independent claim.

### Decision changes

The earlier specification state said no development data existed and implementation awaited owner
confirmation. The owner's instruction to proceed satisfied that first gate. The project is now in
Build with HRR-T1 complete, but only the data contract has advanced: v2 remains the active Human
Knowledge retriever, the canonical RAG remains the sole final-identity authority, and T49 remains
blocked.

During implementation, the initially entered grid constants were checked against HRR-R8 and found
not to match the confirmed spec. They were corrected before the artifact was frozen to the exact
`0.25–0.55 × 0.5/1.0/1.5` grid, and the regression test now locks those values. No candidate output
existed during that correction, so the choice remained genuinely precommitted rather than
result-driven.

### Verification evidence

The deterministic `--freeze` and `--check` paths both report exactly 199 dev cases and
`retrieval_executed=false`. The focused suite passes 10/10 tests covering counts, four-style family
coverage, unique/non-v1 text, unrelated-control boundaries, the exact grid, source/script/output
hashes, deterministic bytes, a non-mutating check, and preservation of existing outputs when an
invalid 41-family source is supplied. Targeted Ruff passes, and strict MyPy reports no issues in the
builder. The pack SHA-256 is
`23589b23567220dbba0de959ec5223cf60365b1222320f3a372f1b156244dbe9`; the manifest binds builder
SHA-256 `3da7becca7b0cb27568e887140d6f07a1e41c0ceb56d0badce38134bca1a776c`.

The complete repository suite passes **211/211 tests** with the known Starlette/AnyIO deprecation
warning. The first whole-suite command did not export `PYTHONPATH=src`: pytest itself found source
modules through project configuration, but a subprocess spawned by an older reproducibility test
did not inherit that in-process path and reported `ModuleNotFoundError`. Re-running the same suite
with the repository's documented subprocess environment passed all tests. Strict MyPy over the new
unittest file also reported the repository's familiar dynamic test-class typing pattern; the
production builder alone passes strict MyPy, while the executable tests verify that dynamic test
behavior. Neither diagnostic changed a frozen output artifact.

### Incomplete work, risks, and next step

Generated controls may not cover the distribution of real marketplace language, and the frozen
grid may expose a recall/safety conflict with no qualifying setting. Those are expected empirical
risks for HRR-T3, not reasons to edit this pack after results. No PostgreSQL data, 3,000-document
load, production/concurrent latency, canonical behavior, or neural embedding is represented here.

The next step is **HRR-T2**: add the experimental character n-gram TF-IDF candidate path, three-
source weighted RRF, typed debug evidence, and fail-closed version metadata without changing
canonical output. HRR-T2 may prove mechanics against fixtures, but it must leave configuration
selection and winner/artifact publication to HRR-T3 using this already frozen pack.

## 2026-09-12 — HRR-T2 experimental character-hybrid implementation

### Context, problem, and observable outcome

HRR-T1 froze the development questions before any new retriever result existed. HRR-T2 could now
solve the underlying mechanics problem without yet optimizing against those questions: v2 requires
an exact shared token before a document becomes eligible, so a query such as `Protn Sagx` cannot
reach the `Proton Saga` family even though their character structure is close.

The new implementation adds an experimental `human-knowledge-hybrid-v3` path that admits candidates
through character evidence as well as tokens. In a controlled implementation fixture, `Protn Sagx`
returns `Proton Saga` first with no sparse rank, character rank 1, and character similarity above
0.7. That family remains debug evidence: the canonical result is still `no_match` with null UUID and
ID. The normal application still runs v2 because there is no selected v3 artifact. No 199-case
development selection, winner, performance report, final holdout, PostgreSQL write, or canonical
change occurred in this task.

### Implementation trace

`src/product_variant_resolver/human_knowledge.py` gains two deliberately separate concepts. Each
typed document now publishes `character_identity_texts`, whose content is narrower than the existing
token-search `searchable_text`: review families allow only casting/aliases, while provisional
variants allow only casting/human-verified labels. `CharacterIdentityIndex` turns normalized spaced
and compact identity forms into Unicode character bigram/trigram TF-IDF vectors and an inverted
posting map. It builds query windows near known identity lengths, gets candidate UUIDs from shared
gram postings, calculates cosine only for those candidates, applies the configured floor, and breaks
ties by UUID.

The v3 retrieval branch ranks at most 25 token and 25 character candidates, unions the IDs, and runs
the existing 192-dimensional `hashing-v1` dense score only on that bounded set. Sparse, dense, and
character ranks then contribute weighted reciprocal rank terms at `k=60`; a missing rank stays null
and contributes exactly zero. The old body was retained as a separate `_retrieve_v2` branch so the
default code path does not accidentally inherit v3 candidate or fusion behavior.

The same module also defines a strict v3 artifact loader. `config.py` exposes only paths to a
selected artifact and the frozen development files—there are no environment variables that accept
arbitrary thresholds. The loader permits only HRR-T1's seven floors and three weights, verifies
every fixed parameter and field allowlist, and checks catalog, projection, development, manifest,
and implementation SHA-256 references. `service.py` constructs v3 only after that validation; index
or retrieval failures cross the dependency boundary as 503 rather than becoming a fabricated result
or a silent v2 fallback.

`schemas.py` adds typed optional character rank/score fields to the common base of both Human
Knowledge candidate variants and a typed character-index metadata object. `service.py` serializes
artifact/version/index evidence only in debug. `api.py` exposes the active Human Knowledge version
and artifact in readiness detail. `ui/index.html`/`ui/app.js` add the Character column and artifact
evidence using the existing safe `textContent` rendering path. The canonical response model is
unchanged.

The tests now cover character-only, sparse-only, compact-spacing, equal-score UUID ties, invalid
floor/short identity, allowlisted fields, posting metadata, strict/stale artifact rejection,
settings paths, debug/OpenAPI/health fields, UI rendering, runtime 503, and exact non-debug canonical
compatibility. The historical v1 builder/evaluator were adjusted only where they had assumed that
the whole mixed v2/v3 source file must retain its old SHA forever.

### Technical choices, alternatives, and trade-offs

The implementation stores character vectors and postings in memory because the corpus has 142
documents and T49 persistence is explicitly blocked. This provides deterministic offline behavior
and keeps HRR-T2 independent of PostgreSQL. The measured structure contains 4,508 posting keys and
19,001 posting entries. That is implementation accounting, not a latency or scale claim; HRR-T3
must still measure both 142 and synthetic 3,000-document scopes.

Both spaced and compact forms were retained. Spaced grams preserve word-boundary information, while
compact grams let `TwinMillGenE` match `Twin Mill Gen-E` without query rewriting. Query windows keep
seller wrappers from diluting every comparison. The cost is more postings and multiple cosine
comparisons per posting-derived candidate. A single compact form would be smaller but would erase
useful boundaries; scoring the full query only would punish noisy marketplace strings.

Candidate-source caps are 25 rather than the final K=5. Five is the fixed selection/report output
depth, whereas each source needs enough recall before fusion. Capping both sources still bounds the
dense union to at most 50 documents and prevents a generic gram from turning dense scoring into an
unconditional 142-document scan. This remains a local deterministic IR design, not a neural
embedding or approximate index.

Artifact-gated activation was selected over a boolean `PVR_V3=true` plus free environment floats.
The artifact path makes version, corpus, implementation, development evidence, and allowed parameter
set one fail-closed unit. The trade-off is that v3 cannot run as the normal application until HRR-T3
writes a valid artifact. That temporary inconvenience is the desired protection against activating
an unselected configuration.

### Decision changes

D37 previously described the character path as proposed and said it had no implementation impact.
It now records that HRR-T1 and HRR-T2 are complete but that v2 remains active. The architecture
choice is implemented; the configuration decision is still intentionally unresolved. Only HRR-T3
may turn one of the 21 precommitted pairs into a selected artifact, and it must publish FAIL if none
meets every gate.

The v1 benchmark stored SHA
`5bf582b921b62945b7e4405beb98822abd876b870bdb5267854764c2e1ab2982` for the original complete
`human_knowledge.py`. Once v3 code was added to that same module, comparing the historical hash to
the live mixed-version file made four regression tests fail even though `_retrieve_v2` output was
unchanged. Rewriting the old benchmark/report with the new file hash would falsely claim that T48
tested code that did not exist. The builder/evaluator now validate the old SHA as the frozen v2
identity and separately require current default v2 execution to reproduce the old output bytes.
That preserves historical truth without using the holdout to tune v3.

### Verification evidence

The HRR-T2-focused unit/integration/API/UI/historical set passes 56 tests. The complete repository
passes **223/223 tests** with the same known Starlette/AnyIO deprecation warning. The development
pack remains byte-valid with 199 cases and `retrieval_executed=false`; the old v1 query pack,
benchmark, JSON, and Markdown remain reproducible. Node syntax checking passes for the UI. Focused
Ruff F/I checking passes for all changed source/tests, and strict MyPy with imported modules skipped
reports no issues in `human_knowledge.py`, `config.py`, and `service.py`.

Two focused tests initially failed for test-assertion reasons: exact floating equality saw
`0.9999999999999999`, so the assertion was correctly changed to approximate numeric equality; the
DOM harness initially inspected the character cell's wrapper rather than its nested rank text, so
the path was corrected. Later, the first full suite exposed the four historical source-hash failures
described above. After separating historical v2 identity from the live mixed file, all 223 tests
passed. A final OpenAPI assertion initially looked for a standalone parent-schema component, but
Pydantic correctly flattens inherited rank fields into both concrete discriminated candidate
schemas; the assertion now verifies `character_rank`/`character_score` on each concrete type. No
development-selection or final-holdout output was inspected during these corrections.

### Incomplete work, risks, and next step

Fixture success does not establish aggregate quality. A floor low enough to recover typos may also
admit generic listings, and a high floor may recreate v2's miss. Human-verified label strings can be
long marketplace titles even though the field itself is allowlisted; query windows reduce but do
not eliminate that noise. The source cap and in-memory posting count still require measured evidence.

The next step is **HRR-T3**: execute exactly the already frozen 21 floor/weight combinations on the
199 development cases, publish raw metrics and every rejection reason, measure the disclosed 142-
document and synthetic 3,000-document cost, and either freeze one checksum-bound artifact or stop
with selection FAIL. Until then, v2 stays active and T49 remains blocked.

## 2026-09-12 — HRR-T3 fixed-grid development selection completes with FAIL

### Context, problem, and observable outcome

HRR-T2 supplied an experimental character-hybrid implementation but had not established whether
any configuration was safe or affordable. This step executed exactly the HRR-T1-frozen 21 floor/
weight combinations against 199 development cases, retaining all 4,179 case/configuration outputs.
The observable result is `verdict=FAIL`, `winner=null`. The active service remains v2; no v3 runtime
artifact, new final v2 query pack, PostgreSQL write or real-catalog expansion was produced.

Positive development retrieval is strong: every setting recovers 164–168 of 168 positives, every
style recovers at least 38/42, every merge control reaches an existing provisional casting (4/4),
and no forbidden family is returned. However, every setting also returns candidates for all ten
generic-no-identity negatives. The ten opaque negatives remain empty. These results cannot be
described as overall success: the precommitted all-gates rule rejects every setting before the
MRR/Recall@1 tie-break can choose anything. This data was transformed from indexed identities,
so even its positive success is development evidence, not final independent accuracy.

### Implementation trace and why these parts changed

`human_knowledge_selection.py` is a separate local evaluator, not a service/ranking change. It
locks both development checksums, verifies non-v1 source references, executes the exact grid with
runtime signal extraction, serializes ordered typed candidates, and only then scores expected
identities. Its checker recomputes raw/style/merge/safety metrics, cost percentiles, rejection
reasons and deterministic selection; it also rejects invented corpus IDs, nonfinite scores,
invalid source ranks and inconsistent weighted RRF. Separating this module prevents development
labels or tuning code from entering canonical resolution. Explicit source-key validation prevents
an incomplete checksum list from silently bypassing integrity checks.

`generate_human_knowledge_selection_report.py` renders the validated JSON rather than recomputing
a different summary. `freeze_human_knowledge_v3.py` implements both conditional paths: FAIL returns
without touching the output; a hypothetical qualified result binds all 21 metric summaries and
the full raw-report checksum, and refuses to overwrite an existing artifact. Unit tests distinguish
this mocked construction behavior from an actual quality PASS. `human_knowledge.py` adds validation
for the freezer's optional `selection_evidence` field, requiring an in-project development-report
path, matching checksum and a matching genuinely qualified winner. T2 ephemeral fixture artifacts
remain compatible without the optional field; T3 freezer outputs always include it. The retriever's
candidate generation, thresholds and ranking algorithm were not changed after results were viewed.

`tests/evaluation/test_human_knowledge_selection.py` covers the fixed grid, guarded no-v1 reads,
every safety/quality/cost rejection gate, all tie-break levels, source/raw/cost tampering, synthetic
scope and conditional freeze/overwrite protection. The existing artifact unit test gains a path-
escape rejection assertion. Reports, QA checkpoint, AI-eval, README and spec statuses now reflect
the actual FAIL and blocked downstream tasks instead of suggesting selection has not started.

### Method choices, trade-offs, and decision changes

The method remains deterministic offline IR: 192-dimensional hashing, character TF-IDF and weighted
RRF. No neural package, new model, scrape, family-slot quota or query rewrite was introduced. Cost
measurement uses a fixed protocol—three warm-ups/configuration, all 199 real queries, and the first
20 case-ID-ordered dev queries on a deterministic 3,000-family synthetic index. Nearest-rank
percentiles and raw samples are saved. Checking arithmetic from saved samples is reproducible;
requiring a new wall-clock measurement to match old bytes would not be honest.

The key decision moves from “select a v3 winner if the frozen grid qualifies” to “retain v2 and
return to design.” For `frd-unrelated-generic-00` (`sealed blue collector model from storage box`),
the 0.55-floor/1.5-weight result still returns five provisional documents through `box`, `collector`
and `blue`, with character rank/score null. This directly exposes an exact-token admission path
independent of the character floor. Expanding that floor grid would not resolve the illustrated
path. Future work must design identity-bearing eligibility rather than select the nearest failing
setting. Likewise, posting indexes alone do not establish cheap scoring: the synthetic corpus has
419,820 posting entries and its shared forms still make comparison expensive. Any optimization
must receive a new decision and measured before/after evidence, not be slipped into this evaluation.

### Verification evidence and execution corrections

The complete suite passes **236/236 tests**, no skips, with one existing Starlette/AnyIO warning.
The complete report passes source/raw arithmetic checks and Markdown byte reproduction; the actual
freeze invocation reports `selection FAIL: runtime artifact untouched, v2 stays active`. Focused
Ruff F/I and isolated strict MyPy on the two retrieval/selection modules pass. Development, family
projection/registry, v1 query/benchmark/JSON/Markdown checks, fixture validation, compilation, Node
syntax and default/PostgreSQL-profile Compose static configuration checks pass. A fresh canonical
fixture report in a temporary directory preserves Recall@25/Top-1/MRR/precision 1.0, false-match
rate 0 and coverage 0.8333. Whole-repository lint/type maintenance debt is not claimed resolved;
SQL/container runtime and concurrency were not repeated.

Two incomplete harness runs were interrupted before report output: the first to finish report/
artifact evidence binding, the second after an isolated type check exposed invariant synthetic-
document list typing. The latter was fixed with the union document type annotation; two earlier
typing findings were resolved by annotating raw counts and casting the selected configuration.
These were implementation/provenance corrections, not threshold, data or metric-driven tuning.
One full unmodified 21-setting execution then produced the committed raw report. Verification also
initially invoked the canonical wrapper without `PYTHONPATH=src` and referenced a nonexistent
separate PostgreSQL Compose file; correct module loading and `--profile postgres` invocations pass.
Neither command mistake required a product change.

On this macOS arm64 desktop with 10 logical CPUs and Python 3.12.13, real 142-document p50 is
8.51–9.70 ms and p95 is **29.37–36.60 ms**, above 25 ms. Synthetic 3,000-document p95 is
**337.15–377.28 ms**, above 150 ms. The real index has 4,508 keys/19,001 entries; synthetic has
2,431 keys/419,820 entries. Measurements are warmed single-process K=5 retrieval on a non-isolated
desktop, excluding index construction, serialization, HTTP, networking, databases and concurrency.
They do not demonstrate 3,000 real records or production scale.

### Incomplete work, risks, and next step

HRR-T3 is complete through its designed no-winner branch, but the feature's final-quality gate is
not complete or approved. HRR-T4–T6 and T49 stay blocked. The next highest-value action is a new
Lite design decision addressing identity-only admission and bounded character comparisons, retaining
this development FAIL and the old final v1 FAIL. A later qualifying code/artifact freeze must still
precede a newly authored, owner-approved unseen final holdout. No such redesign is implemented in
this step. See [raw/report evidence](../reports/family-retrieval-development-v1/selection.md),
[AI-eval](evidence/ai-evals/human-knowledge-retrieval-development-v1.md) and
[checkpoint review](../specs/human-knowledge-retriever-redesign/review.md).

## 2026-09-13 — Propose a new Lite identity-bounded retrieval design after v3 FAIL

### Context, execution and observable outcome

The owner asked for the next step after HRR-T3 preserved a no-winner FAIL. D38 requires a new design
decision rather than another threshold sweep, so this step returned to Phase 1. I reread the frozen
requirements, development evidence and actual sparse/character retrieval code, then authored the
new `human-knowledge-identity-bounded-retrieval` requirements/design/tasks and proposed D39. The
observable output is a reviewable plan for an isolated experimental v4 path. There is no v4 product
code, frozen execution protocol, candidate output, new quality result, runtime artifact or ingestion.

The design addresses the two observed structural weaknesses. Any broad token in human listing text
can admit a document independently of character threshold; generic-00 proves that path with `box`,
`collector` and `blue`. Character posting lookup still feeds a query-window/document-form Cartesian
comparison and per-query sparse frequency scans. I did not rerun a profiler or infer that either
code section accounts for an exact share of latency. The published p95 failures motivate a new
oracle-verifiable algorithm and measured budget, not an unearned speedup claim.

### Files changed and why no product code changed

The three new spec files define casting-only admission fields, a shared frozen whole-token identity
noise policy, complete-core token admission, exact weighted form-posting cosine accumulation with
unknown query grams in the norm, all-or-nothing limits, query-local debug counters and separate v4
artifact readiness. Tasks specify files, evidence and blocked downstream order. README now points
to this proposal while retaining default v2 and the old failures. D39 records alternatives, 10x/
likely failures and six anticipated benefit/risk dimensions; none is reported as a measured PASS.

No code was modified because spec-dev-loop's Lite G1* requires owner confirmation of requirements,
design and tasks before build. Avoiding source-bound v3 modules in the proposed implementation also
preserves the old report's live checksum checks. The new v4 path must integrate through separate
service/config/schema/UI opt-in, not edit historical scoring or silently change its reported version.
This planning pause is a requirement of the skill, not an implementation or quality blocker verdict.

### Technical choices, narrowed decisions and trade-offs

The proposal retains deterministic TF-IDF/hashing/RRF rather than introduce a neural dependency.
It narrows provisional admission from full human-verified listing labels to casting identity; labels
remain stored and broad text may rank already admitted documents. Whole-token filtering avoids
substring rewrites, but can collapse color/common-word names. Complete exact cores are safer than
single-token overlap, but depend on character rescue for partial/typo identities. Unknown-gram norm
handling avoids inflated evidence but can reduce recall. Those risks must pass development and a
later independently authored/owner-approved final test, not be patched by per-case exemptions.

Direct posting accumulation preserves the new formula exactly on small oracle tests, with declared
query/form/posting limits that discard all partial results on budget exhaustion. Such limits do not
guarantee timing and can produce misses. A new scale workload therefore retains the old 20 dev-query
cost probes and adds 100 deterministic target-bearing exact/typo/contextual probes; correctness gates
prevent empty-only fast results from being called scale success. Index/SQL/network/concurrency remain
outside warmed local retrieval measurements.

The old 21-setting grid and all safety/quality/timing thresholds remain unchanged in the proposal.
This is a new architecture/protocol version, not widening the old search. The 199 dev cases are
explicitly already viewed/identity-derived and may be reused as development diagnostics, never as
new blind or final evidence. Original v1 final data remain prohibited for selection. Old v3 reports
and source checksums must remain unchanged. No default deployment or T49 expansion follows planning.

### Verification and incomplete work

Verification results are recorded in `docs/evidence/human-knowledge-identity-planning.md`. They check
the current baseline and documentation scope, not v4 behavior or a speedup. G1* is pending owner
confirmation and all IBR build/evaluation tasks remain unchecked. The highest-value next action is
owner review of the three spec files; once confirmed, IBR-T1 validates actual core/collision/form
limits and freezes/commits a new protocol before any v4 retrieval. If validation fails, return to
design before output rather than quietly drop approved names. T49 and new final holdout authoring
remain blocked. No subagent was spawned and all delivery files stay in the project folder.

## 2026-09-13 — IBR-T1 validates identity cores and freezes the approved v4 protocol

### Context, execution and observable outcome

The owner's `執行下一步` instruction immediately followed the three-spec confirmation handoff, so
this step records approval of the exact requirements/design/tasks at commit `880e4f5` and executes
IBR-T1 only. The goal is to make the new experiment reproducible before its outputs exist, not to
retry the failed v3 grid. The execution protocol now freezes the policy, formula, work ceilings,
unchanged 21 settings, safety/quality/cost gates, all 199 dev query IDs and 120 scale queries/targets.
No v4 retrieval, new rank/metric/latency result, selected runtime artifact or database operation occurs.

The static check finds 142 valid documents and 284 spaced/compact forms, at most 2/document against
the ceiling 32. Two core collision groups contain the already distinct `83 Chevy Silverado` and
`Toyota Supra` variants. These are same-casting version distinctions, not different casting names
collapsing under the policy; all 142 IDs remain separate. No core is empty/too short and no cross-
casting collision occurs. The 199 real queries peak at 90 forms and the scale workload at 60, below
256. These are construction counts, not a scored or timed runtime index.

### Implementation trace and reasons for each file group

`scripts/build_human_knowledge_identity_protocol.py` is an offline deterministic artifact builder.
It reuses the unchanged catalog/normalizer and synthetic document construction, but reads only
provisional casting and family casting/aliases for the core audit. It does not call a retriever.
Strict approved-spec hashes and noise-block validation prevent the code's policy drifting from the
approved design. Stable form IDs, deduplication, gram-reference counts and full collision groups
make future implementation and review inspectable instead of reporting only a total count.

The new `data/evaluation/human-knowledge-identity-development-v1/` contains protocol/manifest, full
real core audit, owner approval and original approved spec snapshots. Snapshots are extracted from
the approved Git commit when freezing, then checks use delivered snapshots without requiring old
Git history. This both preserves attribution and avoids stale integrity checks when live task
checkboxes/statuses change. The snapshots retain historical proposed headers; approval is recorded
as a separate event with actual UTC time, not a retroactive rewrite. Source hashes bind old corpus/
governance/development/v3 evidence and the builder; every delivered artifact is checksum-bound.

`tests/test_human_knowledge_identity_protocol.py` adds 12 checks for portable byte reproduction,
guarded no-v1 reads/no ranking calls, approval/leakage disclosure, exact real/scale counts/targets,
ignored broad human fields, Unicode/whole-token/numeric cores, invalid/empty/duplicate/excessive
forms and query ceilings, all source/file bindings and preservation/idempotence. Evidence, AI-artifact
assessment and scoped QA review separate a valid contract from unmeasured v4 retrieval. README/live
spec statuses and D40 now reflect approval and T1 completion; runtime source files are unchanged.

### Method choices, corrections and trade-offs

The stack remains standard-library JSON/hash/file/Git reading plus existing project models; no
model dependency, external API or PostgreSQL is necessary for protocol construction. Frozen output
checks compare deterministic bytes, and freeze validates all inputs/existing outputs before writes.
Different existing frozen files are rejected rather than overwritten; repeating identical freeze
does not even replace their timestamps. These semantics preserve meaningful pre-output provenance.

An initial freeze attempt stopped before writing because the approved Markdown noise block's fence
language `text` was parsed as an extra token. Stripping that language line fixes the parser without
changing the approved noise set. Initial MyPy checks also needed `MYPYPATH=src` and explicit set
annotations. These were builder/parser/type corrections before v4 output, not data, gate or ranking
tuning. The resulting script and artifacts now reproduce unchanged.

One limitation became concrete during static validation: synthetic `Scale vehicle model NNNN`
casting cores retain only numbers because `scale`, `vehicle`, `model` are approved noise tokens.
The `Scale` → `Scxle` probe edits a removed wrapper, not retained numeric identity. I preserved the
approved workload and explicitly recorded this limitation, rather than change it silently. The
100 target probes still prevent an entirely empty fast implementation from passing, but cannot
prove genuine core-name typo robustness. Real four-style dev quality and independent final tests
remain required. Form-level gram references also cannot be compared to old document postings as
an observed speed/memory improvement; no such measurement was run.

### Verification evidence and next step

Focused tests: **12 passed**. Full repository: **248 passed**, no skips, one existing Starlette/
AnyIO warning. Protocol `--check`, focused Ruff F/I, isolated strict MyPy builder check, compilation
and whitespace checks pass. The old 199-case freeze, v3 JSON/Markdown and v1 final-report checks all
pass without historical source/data/report edits. Protocol SHA-256 is
`31802be99f02698423c4526bbd8752e6f517fcbef8ca8080926d019f55083fde`; its manifest is
`b7634f7f3d52277c4ee4d92489b656fcf1a6c446d56085c5affb7cb7a12c6ea7`.
See [freeze evidence](evidence/human-knowledge-identity-protocol-v1.md) and
[QA checkpoint](../specs/human-knowledge-identity-bounded-retrieval/review.md).

IBR-T1's freeze must be committed before v4 output; IBR-T2 is the next highest-value task: implement
the isolated identity/posting retriever, verify exact scores against a brute-force oracle, and test
query-local budget/debug/canonical readiness isolation. Posting cost, budget-abstention quality and
runtime package evidence are still unmeasured. Default v2, old development/final FAIL verdicts,
blocked final-authoring/T49 and no real-catalog growth remain unchanged. No subagent was spawned;
all delivery files remain inside the project folder.

## 2026-09-14 — IBR-T2: exact identity-posting implementation and isolated runtime evidence

### Context, executed work and observable outcome

The approved v4 protocol existed, but no code could yet enforce casting-only admission or calculate
the new form-posting scores. V3's broad any-token path could admit generic listing words independently
of its character floor, and its full form/window comparisons had failed cost gates. This step completes
IBR-T2's isolated implementation and mathematical/runtime safety checks. It does not rerun selection
or assert that the proposed architecture fixes measured quality or latency.

Callers still get default v2 behavior unless they request a new v4 evidence artifact. A valid v4
retriever now produces casting-core sparse/character evidence, a bounded dense/RRF result and its
own work counters. Generic-only or over-budget queries return no human candidates while canonical
resolution continues. Missing/corrupt requested evidence instead produces readiness/resolve 503.
There is no qualified artifact yet, so normal runtime remains v2 and canonical final authority is intact.

### Implementation trace and why these modules changed

`human_knowledge_identity.py` implements the approved whole-token policy, identity forms, document-level
DF/IDF and normalized weighted gram postings. Direct query posting accumulation avoids reconstructing
every candidate's form/window cosine in the query path. Unknown grams stay in query norms, so unfamiliar
text cannot gain an artificially high score simply by discarding its unmatched features. Exact sparse
admission requires all tokens of one approved identity core; human labels/initial names/series/pricing
never create forms. Dense scores apply only after bounded identity admission, then RRF preserves absent
source ranks and deterministic UUID ties. Budget aborts discard the entire result, including otherwise
exact candidates, rather than publishing a misleading partial shortlist.

`human_knowledge_identity_artifact.py` is an implementation decomposition, not a changed product spec.
It checks the frozen contract/corpora/source hashes and demands a complete, recomputable raw selection
report with a matching qualified winner. Keeping readiness evidence separate from query math makes
both responsibilities testable and leaves source-bound v3 modules unchanged. It defines future report
validation without running the grid or creating a winner. Its positive parsing fixtures deliberately
mock selection validation; they are not development quality evidence.

`config.py` adds a separate v4 artifact setting and rejects v3/v4 conflict. `service.py` selects the
new retriever only from an explicit validated config and retains work inside each resolve invocation.
`schemas.py`, `api.py` and `ui/app.js` expose typed index/form/policy/work/abort evidence while safe-text
rendering preserves inert user/source markup and old payload behavior. Canonical retrievers, policy,
calibration and output selection were not changed. Dockerfile/ignore changes include the protocol-bound
builder and report dependencies in the image context; these are static packaging corrections only.

### Method choices, alternatives and corrections

The stack remains existing Python catalog types, standard-library arithmetic/postings, hashing-v1 and
FastAPI/Pydantic with safe vanilla-JS UI. No neural model, new dependency, network source or database
write is necessary for this eligibility/comparison change. Exact form scores are independently checked
against an all-form/window TF-IDF cosine oracle. An approximate shortlist or type quota could obscure
missed targets; shared last-query debug state could mix requests. The implementation therefore keeps
exact accumulation and immutable returned work values. Four-thread in-process tests check isolation,
not production concurrent throughput.

The initial full test command lacked `PYTHONPATH=src`, causing an existing report subprocess import
failure; the corrected source-path run passes without regenerating reports. A Compose override command
initially named nonexistent files and was corrected to the actual file's PostgreSQL profile. Type checks
needed explicit casts around reused legacy helper contracts, and window-abort debug bounds account for
the two forms added by the detection step. These are implementation/environment corrections, not
after-output tuning of policy, grid, gates or data. No architectural selection was reversed.

### Verification, remaining risks and next step

Core/artifact/API/UI focused tests: **65 passed**; full repository: **311 passed**, no skips, one
existing Starlette/AnyIO warning. Focused Ruff F/I, isolated strict MyPy on new modules/config/service,
Python compilation, Node syntax and whitespace checks pass. The identity freeze, old 199-case freeze,
v3 JSON/Markdown and v1 final JSON/Markdown reproduce with historical hashes/FAILs unchanged. Default
and PostgreSQL-profile Compose/context checks pass; no Docker rebuild/run, PostgreSQL ingestion, full
project lint/type-debt cleanup, latency sampling or 21-grid execution occurred. Detailed limits and
commands are in [T2 evidence](evidence/human-knowledge-identity-implementation-v1.md) and scoped QA/AI
records; live task/README checklists now distinguish engineering completion from quality approval.

Common grams may still exceed the posting ceiling; stricter cores/unknown norms/noise removal can
lose legitimate names. Numeric synthetic identity and wrapper-only typo probes remain limited evidence.
IBR-T3 is next: implement/run the frozen 21-config development and 120-query scale evaluation, publish
all raw outputs/work/timing and apply every gate unchanged. Only a committed qualified winner can
unblock new output-blind final questions and owner approval. Final FAIL must remain FAIL; T49, real
3,000-row catalog expansion, deployment and end-of-project beginner code review remain downstream.
All delivery files stay inside the independent project folder and no subagent was spawned.

## 2026-09-14 — IBR-T3: frozen development selection passes; qualified v4 artifact published

### Context, new execution and observable outcome

IBR-T2 proved the new arithmetic and runtime isolation, but it did not establish real development
quality or cost. This step implements and executes IBR-T3's one frozen architecture experiment:
exactly 21 existing floor/weight settings, every unchanged 199-case development query and the exact
120-query synthetic workload per setting. All 21 pass every predeclared development gate. The fixed
ranking tie-break selects floor 0.50 / character weight 1.0, and its fully evidenced experimental artifact
can now be loaded explicitly. Default v2 and canonical authority remain unchanged; this is not final
quality, a default deployment, database promotion or proof of 3,000 real products.

The selected run finds 168/168 positives, 165/168 at rank 1, MRR 0.9911, 42/42 in all four styles,
merge 4/4, forbidden 0 and unrelated nonempty 0/20. Real/aggregate-scale p95 is 2.07/45.14 ms against
25/150 ms budgets. Known synthetic exact/edit/context hits are 60/60, 20/20, 20/20. Complete raw outputs
and all misses/abstentions are retained, including the two floor 0.55 positive misses; no setting or
sample was dropped, resampled or tuned. A higher floor is not automatically a better configuration.

### Code changes and why these responsibilities are separated

`human_knowledge_identity_selection.py` loads the checksum-valid protocol/corpora, creates the exact
two retrievers for each setting, warms each with three queries and measures only retrieve_with_work.
It serializes all 4,179 real and 2,520 scale results with candidate identities/ranks/work and attaches
expected labels after retrieval is complete. Raw latency, scale subgroup hits/cost and work totals
are retained so summaries can be audited instead of trusted. Source checks before/after prevent mixed
code versions from being frozen. The check command replays arithmetic without any retrieval.

`human_knowledge_identity_artifact.py` adds mandatory runtime-boundary, original-20 subgroup and work-
summary recomputation to its future report contract. These checks were finalized and tested before
real outputs; they change evidence validation, not eligibility, ranking, noise policy, limits or
grid. No checksum-bound predecessor module or v4 query core was edited. Separate readable-report
and freezer scripts keep rendering/publication distinct from selection. Exclusive temporary-file
publication validates artifact bytes with the genuine runtime loader before creating the final path;
existing files are never overwritten, and FAIL does not even create an artifact directory.

`reports/human-knowledge-identity-development-v1/` holds complete JSON and readable tables, while
`config/human-knowledge-retrieval-v4.json` holds the winner and full evidence/source/policy bindings.
Config is intentionally committable, unlike ignored model artifacts/cache. Evaluation tests use an
explicit empty fake retriever for orchestration and no-winner preservation, then separately replay
the genuine report and genuine API artifact. Mock fixtures are not called quality winners. README,
live specs/QA, AI evidence and D42 now distinguish development PASS from the still-unrun final gate.

### Technology choices, corrections and trade-offs

The method remains standard-library Python, existing document models and hashing-v1; no neural
model/API/dependency or SQL write is necessary. One fixed-grid raw evaluation is chosen over an
open-ended threshold search. The original-20 scale subgroup has selected p95 of 61.22 ms, separately
shown against unchanged old-v3 original-20 p95 337.15–377.28 ms. The full 120 aggregate includes easier
exact probes; comparing only aggregate 45.14 ms to old 20 would misstate the workload. Index scoring
representation and non-isolated execution differ, so the observed difference is diagnostic, not a
controlled causal speedup or production SLA. Document/form-gram counts also do not prove memory gain.

An operational issue became visible after publication: temporary-file-based artifacts have host
0600 modes. Docker's non-root pvr could not necessarily read locally copied public evidence. Dockerfile
therefore grants read/traversal on copied public data/config/reports/scripts inside the image, without
changing bound bytes, write permission or the host's private cache. Static context/Compose tests check
this; no new container runtime was claimed. MyPy required an explicit callback annotation for safe
temporary publication. These are packaging/type corrections, not measured-score changes.

The pre-run full test process briefly overlapped first-setting startup/early measurement. I preserved
the run and disclosed this instead of removing/resampling an inconvenient configuration. Runtime
therefore explicitly remains non-isolated: Darwin 24.6.0 / Python 3.12.13 / arm64 / 10 logical CPUs; CPU brand
lookup did not return more than arm. Index/startup, extraction, serialization, HTTP/SQL/network and
concurrent request load are excluded. Synthetic cores remain numbers and Scale→Scxle edits a removed
wrapper, so successful probes do not prove retained-name spelling robustness or real-catalog growth.

### Verification evidence, remaining work and next action

18 new tests, 48 focused T3/artifact tests and 329 full tests pass, no skips, one prior Starlette/AnyIO
warning. Focused Ruff F/I, isolated strict MyPy evaluator/validator, Python compilation, Node syntax,
whitespace and both Compose profiles/context checks pass. Frozen protocol/old dev/v3 JSON+Markdown/
v1 JSON+Markdown remain valid and unchanged. Genuine selected-artifact/API readiness, health/debug
SHA and non-debug canonical equality pass; report checks do not retrieve. No fresh Docker rebuild/run,
real ingestion, final questions/labels/score, whole-feature PASS or default activation was performed.
See [T3 evidence](evidence/human-knowledge-identity-development-v1.md), raw report, QA and AI records.

The selected report SHA is `f52f85f775806d43a57c11e5fa9f7f965da980f54cc58a814d727fdfe7876f42`;
artifact `82c94a2629da6936bec3e4a2983e67c70d69e94cb94a9817375f891d59b1ae6b`. Commit code/protocol/
report/artifact before IBR-T4 authoring. Next is 105 new output-blind final questions, reuse rejection
and owner approval before labels/retrieval, then one final score and runtime/regression closure.
Viewed development can overstate generalization; unseen identity/noise/alias ambiguity remains the
primary risk. T49/3,000-real-row planning remains gated until final/closure PASS. No subagent was
spawned; all delivery stays inside Product Variant Resolver, ready for its independent GitHub repo.

## 2026-09-14 — IBR-T4 preparation: new final query pairs frozen for owner review

### Context, executed work and observable outcome

The development experiment passed and its v4 winner/report/artifact were committed, but final
generalization had not been tested. The approved lifecycle requires new questions **after** that
commit and owner approval **before** labels/retrieval. This step completes only question preparation,
not the whole IBR-T4 task or a final PASS. There are now 105 immutable query/reference pairs and a
complete owner-review table. No owner decisions, expected labels, benchmark, new-final candidates
or score exists. Default v2, canonical authority and the real-expansion/T49 gate stay unchanged.

The pack includes 84 positives, each of 42 approved families with marketplace and lexical questions,
four existing-casting merge controls, seven held-family exclusions and ten ordinary nonvehicle words.
The intended references help the owner judge fairness; they are not model outputs or preapproved
ground-truth labels. Hold means the unapproved family must not be materialized, not that every
provisional candidate must disappear. All questions remain synthetic and same-family, not a live
marketplace or unseen-casting sample.

### Implementation trace and reasons for the changed files

`scripts/author_family_retrieval_query_pack_v2.py` holds explicitly composed question strings, rather
than extracting searchable text or applying a global typo template. It does not import/call a query
retriever or generate expected answers. `family_retrieval_final_v2.py` verifies winner ancestry and
input bytes against commit `a9a3730`, confirms the new pack did not exist there, validates coverage
and static reuse, and builds the query pack/manifest/owner table. A staged directory publishes all
three files together; invalid inputs, existing artifacts and simulated write failure cannot expose
a partial new final folder. Rechecking compares exact case/source/review checksums and timestamps.

Static comparisons cover the old 105 final and 199 dev queries plus 561 indexed/governance/human-label
strings. They reject normalized/compact duplicates and nonempty old query identity-core equality,
without changing the normalizer/noise policy or trying new candidates. All 42 paired families and
4/7 controls are present; ten unrelated words have zero corpus-token overlap. This does not guarantee
zero character matches or semantic independence. The new tests guard no-new-retrieval/no-old-final-
label/result reads, cover invalid references/styles/counts/labels/metadata/stale sources, repeat-freeze
preservation, atomic publication failure and genuine frozen pair hashes. Temporary Git fixtures are
mocked only after a separate real committed-winner proof.

Live specs, README/QA, D43 and AI evidence now say T4 **preparation** complete but owner approval
pending. All delivery remains in the independent project folder. Source-bound v4/v3/runtime files,
selected report/artifact, existing final benchmark/FAIL reports and data corpus were not edited.

### Method selection, correction and accepted limitations

The stack is existing Python plus standard-library Git subprocess/JSON/normalization/hash/staging;
no new dependency, database/network operation or subagent is needed. Explicit strings preserve varied
marketplace context, spelling, spacing and numeric wording. Machine-score screening would bias final
questions toward success, so the new questions were not queried or filtered by retrieval performance.
The author does know previous development results and model rules: output blindness is limited to
these new candidates, not an independent author/population claim. Human review cannot remove every
construction bias but provides attributable relevance approval before formal truth.

A pre-approval metadata mistake was caught while checking the old final formula: coverage was named
`positive_coverage`, while the inherited 0.90 gate is **family_coverage_at_5 over 42 groups**. I preserved
that unapproved initial pack/manifest/review and exact author-source snapshots in a superseded folder,
then corrected the field name and re-froze the identical 105 cases. No question, threshold, model,
approval, label or candidate output was changed or used for this correction. The old draft SHA is
explicitly ineligible for approval/scoring; the authoritative current SHA is presented to the owner.
This is a contract-fidelity correction before scoring, not relaxed acceptance or a new fitted metric.

### Actual verification, pending approval and next permitted work

22 new focused tests and 351 full repository tests pass, no skips, one prior Starlette/AnyIO warning.
Focused Ruff F/I, isolated strict MyPy live authoring module, Python compilation, Node syntax, whitespace
and static default/PostgreSQL-profile Compose checks pass. The authoritative query check and old
identity protocol/dev/v3 JSON+Markdown/v1 JSON+Markdown reproduction pass. These engineering checks
do not establish final ranking quality; full-suite retrieval tests use existing fixtures, not this
new 105-question final set. No fresh container runtime, SQL promotion or real 3,000-row ingestion ran.

Authoritative query SHA is `b23b69912c678c027461c96eb23f113484c5a8ed6218c06d90026704abe5102b`;
freeze time 14:15:13Z follows winner commit 14:04:23Z. See
[all 105 owner-review pairs](../data/evaluation/family-retrieval-v2/owner-review.md) and
[freeze evidence](evidence/family-retrieval-final-v2-query-freeze.md). Per-case checksums and input
fingerprints are in the manifest. The next action is **explicit owner confirmation of those exact
pairs/checksum**, or Case IDs for a versioned pre-score revision. Stop here under Lite/spec-dev-loop;
approval/label/scoring implementation is intentionally deferred. After approval, freeze attributable
labels and commit benchmark before one final score, then runtime/regression closure. Unseen typo/
numeric/alias ambiguity and negative character overlap remain risks; T49 is still not authorized.

## 2026-09-14 — IBR-T4 owner-approved family labels and benchmark

### Context, problem and observable outcome

The105 output-blind questions were frozen but deliberately had no formal answers because owner
consent was missing. A generic next-step message did not close that gate. The owner then explicitly
confirmed the validation targets and raised an important scope question: colors and distinguishing
features matter as much as casting for the final product. I inspected the actual signal/identity/
structured-ranking/policy code and explained that existing color/year/series/number mechanisms
do not amount to complete wheel/tampo or real variant validation. This105-question pack validates
casting/family retrieval only. After that explanation, the owner replied `沒有問題，請繼續下一步`.
The approved targets now have105 attributable, reproducible family-level answers and a frozen
benchmark, without running any of their retrieval queries or inferring release/canonical truth.

### Code changes and why they are separate

The new `src/product_variant_resolver/family_retrieval_final_v2_labels.py` validates committed
question/review bytes at8f28918 and the existing winner/input chain, derives labels from the frozen
registry/projection/human casting data, records actual conversation excerpts, and provides strict
label/source/metadata and commit-before-score checks. The new
`scripts/build_family_retrieval_benchmark_v2.py` offers exclusive freeze, pure validation and
committed validation commands. Keeping these separate is necessary: the previous question author
and v4 runtime/evaluator sources are checksum-bound and must not be retroactively changed. Their
pending-review flags describe a historical freeze, not the new approval status.

The three approved documents are published together under `data/evaluation/family-retrieval-v2/
approved/`, preserving the original questions. Positive answers name review-family IDs/UUIDs;
merge answers name provisional casting IDs/UUIDs, not release UUIDs. Held controls exclude only
the held identity and may return other legitimate evidence; unrelated controls require no hits.
The manifest binds every case and all input/builder bytes. The new28-test label suite checks
exact mappings, missing/partial/duplicate/rejected approvals, generic-only proceed instructions,
changed queries/targets/gates/scope, stale builders, bool/int substitutions, recording times,
repeat-preservation, partial-publication failure and commit gates. The old query test was narrowed
to immutable top-level files so a legitimate separate approved child does not invalidate history.
Live design/tasks/QA/README, evidence/AI rubric and D44 now describe this completed label stage.

### Method choice, trade-offs and decision boundaries

Existing Python standard-library JSON/SHA/Git/private staging is sufficient; no new dependencies,
agents, database writes or external model are needed. Reusing confirmed registry targets avoids
inventing colors or converting provisional labels to canonical truth. Publishing one complete
child directory was selected over writing three independent final files, which could leave a
partially approved benchmark after an interrupted write. Exact type-sensitive reconstruction
guards against metadata and scope drift; the scorer must also prove committed, unchanged bytes.

Consent is recorded as a whole-pack target approval, not105 independent hand-labeling events or
cryptographically signed identity evidence. Recording time16:36:32Z is available; actual message
timestamps are not, so the record stores null rather than inventing them. The version's context
validator requires the actual target/scope/proceed excerpts, not a generic consent NLP classifier.
At10×, data validation and SHA reads grow with artifact size but do not run retrieval or train a
model. The most damaging failure would be promoting family answers to release truth; explicit
scope and tests prevent that claim. No threshold, query, identity policy or winner decision changed.
The earlier broader variant goal remains required work, not implicitly satisfied by family tests.

### Verification actually run

28 new label tests and50 combined query/label tests PASS; the correct
`PYTHONPATH=src .venv/bin/python -m pytest` invocation passes379 tests, no skips, one existing
Starlette/AnyIO deprecation warning. The initial full invocation omitted PYTHONPATH and had
378 pass/1 subprocess module-resolution failure; fixing the launch environment, without product
edits, resolves it. The first Node check named a nonexistent nested UI path; the correct
`node --check ui/app.js` passes. Focused Ruff F/I and isolated strict MyPy, compilation, current
label and original question validators, v4 JSON/Markdown replay, protocol, v1 benchmark/Markdown
reproduction PASS. These are actual engineering checks, not final-v2 ranking or runtime benchmarks.
The actual precommit benchmark CLI refuses scoring eligibility until the label artifacts are committed.
No fresh container/HTTP/SQL/load check or real3000-product ingestion ran.

### Remaining risks and next step

See [approval/label evidence](evidence/family-retrieval-final-v2-label-freeze.md) for all artifact
hashes and consent details. Query SHA remainsb23b6991; the benchmark is now frozen independently.
The final-v2 retrieval/ranks/score are still absent. Next commit/push this benchmark and verify
its commit gate, then T5 performs one final evaluation followed by runtime/full regression closure.
Synthetic same-family author bias, alias/typo ambiguity and true variant-data gaps remain disclosed.
Defaultv2 stays unchanged; old FAILs, real SQL promotion and T49/real expansion remain gated.

## 2026-09-14 — IBR-T5 pre-execution evaluator freeze

The committed105-question family benchmark at87bbd19 permits one final score, not final-set tuning.
I added a separate `family_retrieval_final_v2_evaluation.py`, report entry script and28 fake-output
tests rather than changing source-bound v4/label modules. Separate preflight integrity validation
checks committed inputs; the collector does not open approved labels, retrieves each question
exactly once with zero final warmups, and durably saves all ranks/work/errors before scoring.
An exclusive run reservation survives interruptions, deliberately preventing a convenient rerun.
JSON/Markdown check reconstructs fixed gates,84/42/4/10 denominators, all misses/safety/errors and
nearest-rank diagnostic samples without retrieval. The new code is committed before any final run.

Standard-library subprocess/JSON/hash/exclusive publication reuses the existing stack. Tests use
fake rows, not live final retrieval. They exposed insertion-order differences in dict-rendered
Markdown; stable sorted JSON rendering fixes byte reproduction before any real score. A temporary
preflight fixture lacked copied source files; adding the private fixture files fixes the intended
ValueError assertion rather than altering production behavior. Initial full run406 pass/1 fixture
failure is preserved as development evidence; corrected results are recorded at closure.

The independent `verify_human_knowledge_v4_runtime.py` runs real loopback Uvicorn HTTP within a
non-root/read-only Docker container using only old fixture queries, with isolated tmpfs and no host
port or PostgreSQL service. It checks default/v4 canonical equality, health/debug/UI and missing/
malformed/stale mandatory evidence503, then binds the report to image/runtime source hashes. Docker
socket access requires sandbox escalation; the authorized read confirmed Docker Desktop available.
An initial dedicated image built successfully; current-code rebuild and runtime checks follow.

No model rule, artifact, query, label, threshold or canonical authority changed. Before execution,
all existing report FAILs and source-bound bytes remain untouched. Final quality is still unviewed;
next is the single real run, followed by full/runtime/historical verification and honest PASS/FAIL
closure. Synthetic family accuracy cannot prove release/color/wheel/tampo or production accuracy.

## 2026-09-14 — IBR-T5 single final score and Lite/runtime closure

### What ran and what problem it closes

The approved benchmark87bbd19 and new evaluatorb86578c were committed before any real final
output. I ran exactly105 final queries once with the selected0.50/1.0 v4 settings, zero final
warmups/retries. A separate preflight process validates committed labels/source integrity; the
collector itself does not open approved labels. All raw results are saved before the runner parses
answers and scores. The frozen9 gates all PASS: positive80/84@5,77/84@1,MRR.93254; marketplace
42/42,lexical38/42; family42/42; merge4/4; forbidden/unrelated/errors0. Four lexical misses remain
empty and fully published, rather than being repaired against viewed final queries. This closes
the scoped family-retrieval quality checkpoint, not complete release/color/wheel/tampo accuracy.

### Code and evidence changes, with reasons

`reports/family-retrieval-v2/` now contains immutable run-start/raw/evaluation JSON and readable
Markdown. The evaluator's pure checker reconstructs raw candidate IDs/UUIDs/source ranks/RRF/
work/budgets, event order, fixed denominators, every gate and text from stored evidence without
retrieval. No pinned retriever/normalizer/loader/artifact/question/label bytes changed after output.
The additional `test_human_knowledge_v4_closure.py` checks genuine stored final data, Docker-root/
non-root packaging requirements, runtime source/image/503/canonical evidence, and preserved
failure records. Unlike orchestration fixtures, it does not execute a real final query.

Fresh Docker testing exposed a real deployment-path bug: defaultv2 started, but v4 returned503
because an installed module derived ROOT as/usr/local/lib/python3.12, while evidence lives/app.
`Dockerfile` now sets `PYTHONPATH=/app/src`, reusing exact bundled source bytes and existing
project-relative evidence layout. This is a packaging correction, not a new retrieval architecture.
It avoids editing checksum-bound loader/runtime code or weakening evidence checks, and keeps
dependency installation in the image while executing the validated source tree. The dedicated
old failing image and observed traceback/health failure are retained, not overwritten as PASS.

The independent runtime verifier first incorrectly used relocation of identical artifact bytes
as its stale sample. With a fixed/app root, valid bytes still correctly validated against the full
evidence chain. I corrected only that test fixture to corrupt mandatory selection evidenceSHA;
the original missing/malformed/stale health/resolve503 requirements still apply. Its initial
assertion failure is also retained. The verifier now additionally records its own and Docker/
Compose packaging hashes, binding the actual HTTP smoke to the exact successful image and files.

### Technical choices and accepted trade-offs

The evaluation remains standard-library/existing deterministic v4 retrieval; no model, threshold,
query policy, database or agent was added. A durable exclusive reservation is intentionally less
convenient than overwrite/rerun, but makes one-shot output and interruptions auditable. Separate
integrity validation necessarily sees labels only for preflight; collection/scoring does not parse
them until all105 raw outputs exist. Fixed42-family coverage measures either paired hit, not an
inflated84-row denominator. The fourmisses and known construction bias are explicit limitations.

Real HTTP within a non-root/read-only container was selected over claiming host TestClient/static
checks prove packaging. It exposed the site-packages/data layout mismatch that prior static checks
missed. Loopback Uvicorn uses no published host port and only existing fixture questions, not a
second final run. Temporary child servers and the test container are cleaned up; previous service,
volumes and PostgreSQL are untouched. Old images remain for diagnosis. The verifier is mounted
read-only rather than added as a runtime dependency. At10×, source-valid T3 posting-cost results
remain the synthetic budget evidence, not a claim of3000 real released variants or production load.

### Actual verification and measurement scope

32 new evaluator/closure tests and411 full repository tests PASS, no skips, one pre-existing
Starlette/AnyIO BlockingPortal deprecation warning. Before real execution, a dict-rendering-order
bug in fake report Markdown was fixed with sorted JSON and a private missing-source fixture was
corrected; its406pass/1fail full run preceded the407-pass pre-final run and evaluator commit.
The final full run411 and32focused cover stored evidence or fake retrieval, not a rerun of final.
RuffF/I, isolated strict MyPy evaluator, compilation, Node UI and static default/postgres Compose
checks pass. Originalv1 benchmark/report/Markdown,199dev,v3FAIL JSON/Markdown,identity protocol
and v4PASS JSON/Markdown reproduce unchanged. Historical full-repo lint/type debt is not claimed
fixed. Source-bound T3 real/scale p95=2.065375/45.138542ms and known-target budget gates validate.

The final105 diagnostic samples use Python3.12.13/Darwinarm64, one non-isolated process, zero
warmups and nearest-rank p50=2.591583/p95=6.945209ms. Extraction is excluded; retrieval plus
serialization included. No new latency gate or causal/HTTP/SQL/production claim is made. Successful
Docker smoke uses Python3.12.14/Linuxaarch64/uid100/read-only and actual loopback HTTP, validates
defaultv2/v4 health/resolve/UI200, identical canonical outputs, typed debug/work/index metadata,
and missing/malformed/stale503. Source and packaging hashes match the host; image identity and
all outputs are in the runtime report. No new SQL or3000-real-row insertion occurred.

### Remaining work and exact next authority

See [final/closure evidence](evidence/family-retrieval-final-v2.md), all105raw results and both
preserved runtime failures. New final quality, source-valid cost, regressions, runtime packaging,
QA/AI rubric and documentation all pass for this feature. T49 DESIGN ONLY may now proceed;
actual promotion/ingestion/defaultv4 deployment is not authorized. The next valuable design work
is a reviewed real release-variant catalog and same-casting color/year/wheel/tampo test cases,
including ambiguous/insufficient-evidence behavior, before expanding toward3000 real rows or
claiming the user's full variant-resolution goal. OldFAILs/defaultv2 and canonical-only final
authority remain unchanged. Commit/push all real progress to the project-only GitHub repo.

## 2026-09-14 — T49 persistence and real-variant roadmap draft (Lite)

### Context, problem and observable outcome

IBR-T5 ataf27dfe permits T49 design only. The user's next-step request follows a scoped family
PASS, not complete variant correctness. I inspected actual canonical schema/identity/signal/catalog
code and source counts before proposing expansion. Human RAG has100provisional+42family docs;
Wiki100release rows all have null color and no dedicated wheel/tampo fields. Existing canonical
identity has seven fields, not wheel/tampo or series-position identity. Consequently, persistence
alone cannot solve the requested color/feature distinctions, and a3,000-row quota cannot replace
evidence/review. The result is a reviewable draft roadmap, not new products or a completed database.

### Changed files and why no product code changed

New `specs/human-knowledge-persistence-and-variant-roadmap/{requirements,design,tasks,review}.md`
defines observableR1–R14 boundaries, proposed snapshot/observation/evidence/review tables,
interfaces/errors/verification and atomic bounded tasks. T49 first plans preservation/measurement
of142typed knowledge documents; a separate release lane starts from100heldsource observations.
The first proposed implementation task is a local-only142doc import-plan validator. It performs
no SQL/network operation. Subsequent isolatedDB/profile/source/release decisions are explicitly
gated. This avoids repurposing canonical `product_variant` for unreviewed evidence or retroactively
editing scored v4/config/identity files whose hashes are already frozen.

`docs/REAL-CATALOG-ROADMAP.md` gives a Chinese beginner-readable explanation of the difference
between saving data and confirming release truth. Source-scope/AI evidence and README progress
now distinguish planning delivery from owner approval/implementation. D46 records the proposed
method and accepted uncertainty. No product Python/API/SQL/migration/runtime/config/data file was
edited, and no family/variant decision was recorded. Requirements/design/tasks are all DRAFT.

### Method choice and trade-offs

PostgreSQL/SQLAlchemy/Alembic is proposed because the project already uses that stack and needs
transactional snapshot/provenance persistence; files-only remains the unchanged default until an
optional profile is independently validated. Versioned JSONB human payloads preserve exact142doc
types/UUIDs; structured field observations and append-only reviews make release conflicts visible.
Reusing canonical tables or a single free-text blob would erase the crucial authority/evidence
distinction. Persistence adapter changes require new source/config/report versions, not silent
edits to scored code. ANN/neural/photo/OCR changes are not bundled into this storage decision.

The release method preserves nulls and field evidence; it does not guess colors from year lists,
toy IDs or filenames. Same-casting/different wheels/tampo can stay separate, while missing fields
cannot prove equivalence. Future identity-v2 must be explicitly designed from real discriminator
evidence, preserving legacy UUIDs. At10×, real source requests, review work and SQL/network/posting
cost are the constraints to measure; no cheap scale conclusion is drawn from storing more rows.
Most likely failure is treating a family approval or database row as confirmed release truth.

Approximate3,000count is narrowed to unique real staged source releases, reported separately
from observations/castings/held/reviewed/canonical rows. Proposed100→500→1,500→about3,000batch
milestones are plans, not execution or permission. There is no policy/threshold/source revision
change based on the viewed final105cases; those results remain immutable and are not queried again.

### Verification and source-access limits actually observed

Read-only `jq` counts/keys and SHA reads confirm97human castings/100provisional groups,
42acceptedknowledge families,42new/4merge/7hold registry,100source rows/all100color-null and
absent dedicated wheel/tampo keys. Committed benchmark and stored finalJSON/Markdown checks
PASS without retrieval. New document links/whitespace and unchanged source hashes are checked
at handoff. Upstream411tests/runtimePASS remain existing evidence, not newly implemented T49 tests.
No DB startup, writes, remote row collection, images, canonical minting or source data edits ran.

Read-only web checks found the official MediaWiki API etiquette page accessible; Fandom licensing
and the Hot_Wheels page returned402 through the browsing service. That tool response does not
prove all API access forbidden or permitted; current source-specific rights/access/robots remains
unverified and gates later collection. General serial/request identity/cache advice is linked in
design; it does not grant Fandom permission. No bypass was attempted. HistoricalCC-BY-SA source
metadata is retained as historical attribution, not upgraded to present legal clearance.

### Remaining work and next owner decision

See [plain-language roadmap](REAL-CATALOG-ROADMAP.md) and
[source-scope evidence](evidence/t49-planning-scope.md). Under spec-dev-loopLiteG1*, pause for
requirements confirmation first, then design and task confirmations. This draft's acceptance
does not itself start a database or authorize3,000-row crawling/canonical promotion. The next
bounded approved implementation would produce the142doc import PLAN, preserving all current
runtime/data/UUIDs. Actual variant grouping/evaluation and canonical rollout remain future work.
All draft progress is committed/pushed only within the independent project GitHub repo.

## T49.1 — 本機 142 筆人工知識匯入計畫與完整性檢查

Date:2026-09-14. Lite mode. This entry records local implementation, not PostgreSQL ingestion.

### 執行內容、問題與可觀察成果

你在詳細草案說明後要求「請幫我執行」，本次將授權限縮為第一個本機任務 T49.1。
沒有將這句話記錄成三次獨立規格確認，也没有假定整份資料庫／蒐集／版本上線方案已獲同意。
先前已有 100 筆 provisional variant 與 42 筆 review family，但缺少一份能在未來匯入前
證明「來源同版、內容完整、ID 沒變、待審限制仍在」的可重現計畫。現在產出的
[plan 與中文報告](../reports/human-knowledge-snapshot-v1/report.md)補上這一層，讓下一步不是
直接把不明版本的資料寫入資料庫。這次新增的是工具和報告，資料集筆數沒有增加。

### 修改位置與原因

新增 `src/product_variant_resolver/human_knowledge_snapshot.py` 管理來源指紋、typed document
序列化／還原、完整計畫重建比對、中文報告與 exclusive publication；新增
`scripts/plan_human_knowledge_snapshot.py` 提供 `--run`／唯讀 `--check`。採用新檔案而非修改
現有 human RAG／config／API／identity，是因為後者已被評估來源指紋封存，不應為儲存準備
偷偷改變其執行行為。既有 typed loader 僅被讀取重用，不重新建立 UUID 或改 ranking。

每筆計畫保留原有 ID、UUID、knowledge type、全部 typed payload，以及原始 casting／variant
或 family／registry entry。只保存 typed payload 會漏掉 failure categories、casting-family-only
層級與人工決策／held release references，所以原始 metadata 也一起保留。來源合約原樣保留，
特別是 `postgresql_ingestion` exclusion；本計畫不是解除限制或正式匯入許可。4 個 merge-source
family 與 7 個 held family 不另建文件，42 個已接受 family 的 79 個 source rows 保持原樣。

### 方法選擇、取捨與決策界線

本次只需要本機 JSON 和 SHA256，因此使用 Python 標準函式庫，沒有增加 SQL／HTTP／ML
依賴。對 12 個直接來源檔案固定已確認版本的指紋，比僅相信 manifest 安全：若資料與
manifest 一起被改，兩者雖然相符，仍可能不是原來的資料。本工具會拒絕。整份 plan 從
固定來源重建再比對，因此即使竄改內容後重新計算 checksum，也不能通過驗證。比對以
JSON bytes 進行，避免 Python 把 `False` 與 `0` 視為相同。snapshot ID 是內容指紋字串，
不是新增商品 UUID。12 檔的 immediate source envelope 不等於重新驗證全部歷史 evidence tree。

另一個取捨是為稽核保留部分重複原始內容；142 筆規模可以接受，但未來 10 倍資料量下
檔案大小與版本審查成本會增加，不能據此宣稱查詢或 SQL 效能足夠。來源變更必須建立
重新審核的新 snapshot 版本，不能修改 v1 指紋假裝舊報告仍有效。D46 的資料表方案仍是
提案，D47 僅接受這個本機方法，沒有重新選擇或啟動 PostgreSQL 技術棧。

報告只發布至專案 reports 下新資料夾；同名再次執行直接拒絕，不覆蓋既有成果。
正常失敗只移除本次建立的檔案，未知／他人檔案保留。若程序被強制中止可能留下不完整
資料夾，checker 會拒絕、重跑也不會覆蓋；這不是 crash-atomic DB transaction 的保證。

### 實際驗證結果

實際讀取並產生 142 筆計畫，`--check` PASS；全部 ID／UUID／typed fields 完整 roundtrip。
新增 37 個測試 PASS，涵蓋每一個來源指紋、缺檔、重複／缺漏／held／錯誤 type 或 UUID、
重算 checksum 後的竄改、原始來源與 exclusion 變動、重複發布、symlink、未完成報告、
失敗清理與保留未知檔案。守衛測試確認新計畫只讀取宣告的 12 個本機輸入，不讀 final queries。
完整回歸 448 tests PASS；唯一 warning 是既有 Starlette／AnyIO BlockingPortal deprecation。
Ruff F/I 與隔離 strict MyPy PASS，compile/static compose/stored final integrity checks PASS。
這些是本機／靜態驗證，不是新的 SQL、容器部署、檢索延遲或版本辨識準確率結果。

plan content SHA256 為 `f7830e460650e99ab5107ec0f049c96d2dcf322daa5c140c5847a53f969e144f`。
格式化 JSON 的檔案 byte hash 與內容 hash 不同；詳見
[執行界線與證據](evidence/t49-1-execution-scope.md)及 [AI artifact rubric](evidence/ai-evals/t49-1-snapshot-plan.md)。
原始資料、已封存模組、final 評估輸出維持不變，沒有啟動新的 final collector。
網站新請求 0、PostgreSQL 寫入 0、新 canonical UUID 0、新真實資料列 0。

### 未完成項目、風險與下一步

T49.2 尚未執行。下一步先指定並確認可丟棄的隔離測試資料庫環境與限定 schema/import
方案，才建立 human snapshot tables 與交易／rollback／idempotence 測試；不能沿用不明
既有資料庫或重設 volume。Human RAG 仍是 debug-only；142 筆儲存不等於 142 筆正式商品。
顏色／輪圈／tampo 等版本證據與約 3,000 筆真實來源蒐集仍是後續獨立工作，本次未確認
網站權限、未推定未知特徵、未改預設 API／v4 rollout。依 Lite 閉環更新任務、QA、decisions
與這份敘事日誌；所有成果限定在独立 Product Variant Resolver repo。

## T49.2 前置檢查 — 隔離測試環境待確認

Date:2026-09-14. Lite mode. No database implementation or write is claimed in this entry.

你要求進行下一步後，本次先確認規格、canonical migration、原有 PostgreSQL importer／
verifier 與 Docker 配置。T49.2 的前提是明確選定隔離測試資料庫，不能將「下一步」視為
操作不明既有 volume 的授權。原有 compose 使用 `pvr-postgres-data` 持久化 volume，
因此沒有直接執行 compose up、migration 或 importer。這解决了測試可能誤碰既有資料的
環境選型問題，但尚未完成 human snapshot 持久化。

唯讀 Docker inventory 起初因 sandbox 無權存取 docker.sock 而拒絕；取得唯讀檢查權限後
查詢成功，沒有執行中的容器，本機已有 PostgreSQL16／pgvector 映像。未檢查或推定所有
stopped containers／volumes 都是空的，也沒有清理任何既有資源。T49.1 的本機 plan
checker 再次 PASS，142文件與來源指紋保持不變；没有重跑 final collector。

新增 [隔離測試方案](T49-2-ISOLATED-TEST-PLAN.md)，說明 internal network、新專屬容器、
tmpfs、無 host port、無既有 volume／使用者資料庫 URL，以及只清理本次 ownership 資源
的提議。選擇臨時新庫而非沿用持久化庫，是為了將可丟棄的交易驗證與工作資料分開；
沿用本機既有 image 避免不必要的下載與版本漂移。tmpfs 不驗證斷電耐久性，不能把結果
升級成正式部署或 crash recovery 證據。將來10倍資料量的 SQL／查詢效能仍需獨立 protocol。

方案也明确說明，120canonical synthetic fixture 僅供新測試庫建立前後不變基準；
142human docs 儲存在独立 human namespace，不是新增正式商品，也不解除原始來源的
canonical／ingestion 排除。確認後才新增 additive migration、repository 與 SQL verifier，
驗證 roundtrip、transaction rollback、相同 snapshot no-op、collision rejection 和全部
canonical rows／IDs／timestamps 不變。本次只修改方案與日誌，未寫產品碼、資料或 SQL；
沒有新增測試結果或完成標記。依 spec-dev-loop Lite 的環境界線暫停，請 owner 確認新
隔離測試庫及限定寫入／清理範圍後，再執行 T49.2。

## T49.2 — 人工知識 PostgreSQL 隔離匯入與真實交易驗證

Date:2026-09-14. Lite mode. Scoped SQL correctness PASS; not production integration.

### 新執行內容與解決的問題

在隔離方案說明後，你指示「執行測試」，因此本次實作並執行 T49.2 限定的新測試庫，
不再停留在 T49.1 的本機匯入 plan。原先缺少的是「142 筆寫入資料庫後仍可完整還原，
而且中途失敗不會留下半份資料」的真實 SQL 證據。現在在 PostgreSQL16.14 實際完成
100provisional variant +42review family 的匯入／讀回／比對，保留原始 ID、UUID、
typed fields、null、raw provenance 與來源排除界線。這142筆仍是人工知識，不是142筆
已確認商品；沒有新增真實 dataset rows、推定顏色／輪圈／tampo 或建立 canonical UUID。

### 修改位置與設計原因

新增 `migrations/versions/0002_human_knowledge_snapshot.py`，只建立獨立 `hk_snapshot`
與 `hk_document`，不改 canonical0001/history。Snapshot 保存 storage version、獨立 test
namespace、固定 plan header/source/contracts/counts/checksum 與 imported_at；子文件保存
原有 ID／UUID／type、順序、完整 typed payload／checksum 與原始來源。把人工知識放進
`product_variant` 會模糊審核權威，所以保持兩条儲存路徑；embedding／release tables 尚未建立。
加入0002會讓 migrationhead 前進，但不改 canonical schema 或 API/default/v4 行為。

新增 `human_knowledge_persistence.py`，在連線前複製並驗證整份固定來源 plan，只允許
明確 disposable authorization 與 matching `pvr_t49_2_<12hex>` DB 名稱，連線後再次驗證
actual database。沒有 `.env` 或正式 database URL fallback。這是另外授權的
`human-knowledge-isolated-storage-test-v1` 保存／測試命名空間，不修改或解除來源本身的
`postgresql_ingestion` exclusion，也不授權 canonical ingestion。Repository 沒有 overwrite
upsert／update／delete 修復路徑；來源或既有 stored snapshot 不完整、竄改就拒絕。

新增 `scripts/verify_human_knowledge_postgres.py` 執行真實 SQL 測試；新增
`scripts/run_human_knowledge_postgres_test.py` 管理只屬於本次的 network／containers、
staging、immutable report 與精確 ownership cleanup。新增兩組測試共25項，分開驗證
repository orchestration 和 supervisor safety；本機 fake 不拿來宣稱 PostgreSQL rollback。

### 方法選型、取捨與調整原因

沿用專案已有 PostgreSQL16／SQLAlchemy2／Alembic，而非換資料庫或新裝 ML stack。
單一 `engine.begin` transaction 配合兩張 human tables 的 SHARE ROW EXCLUSIVE locks，
使完整142筆一起 commit／rollback，也讓同時第一次匯入只能有一個寫入，另一個核對後
no-op。鎖只作用於 human tables，不改 canonical rows。讀回使用 explicit ID+hash、
repeatable-read read-only transaction，避免讀取 latest snapshot 或跨兩次 SELECT 出現不同版本。
這是142筆的小規模簡化；10倍規模下鎖競爭、JSONB／raw provenance 大小與查詢成本仍需量測。

實際前置檢查發現 host venv 沒有 SQLAlchemy，部分原始 family files 權限為600。
選擇既有 SQL-enabled Docker image 搭配 byte-exact staged source 副本，不安裝 host 依賴、
不改原始權限、不重新下載／build image。副本只有必要 Python／migration／config／data／
plan 共54檔，没有使用者 `.env` 或 final questions；report 記錄每個檔案指紋與完整 image IDs。
Optional SQLAlchemy 使用 lazy import，避免未選用資料庫的 offline 路徑強制安裝依賴；
首次 static checks 的 import ordering／缺少 optional stub／Any-return 問題在 SQL 執行前
修正，focused Ruff 與 isolated strict MyPy 再次 PASS，沒有以放寬來源驗證處理問題。

臨時庫使用 tmpfs、新 internal network、無 host published port、不掛既有 volume，runner
UID100/read-only root/read-only staged bind。SQL 測完只依本次完整資源 ID 與 ownership label
移除兩個容器和 network，未接管既有 stopped containers。tmpfs 不是持久性／斷電復原證據，
程序強制中止仍可能留下 owned resources；不宣稱 cleanup crash-atomic。Application importer
維持完整性與 immutable snapshot，但 superuser 手動 SQL 仍可竄改；讀取／重匯入偵測後拒絕，
不是透過 trigger 阻止所有 privileged writes。

另一個相容性界線：歷史 T04 verifier 使用 `upgrade head` 卻固定斷言0001，它是舊 revision
測試，不宣稱可直接用於新0002。保留其歷史來源，改由新的 T49.2 verifier 驗證
0001→0002→0001→0002 的限定循環；沒有改舊斷言或把未執行的 legacy CLI 說成 PASS。

### 實際 SQL 與回歸結果

第一次真實 SQL invocation PASS，未重試。PostgreSQL16.14/Linuxaarch64、Python3.12.14、
SQLAlchemy2.0.52／Alembic1.20.0／psycopg3.3.5。真實 unique violation 在 header 與71筆
子文件已可見後觸發，transaction 完整回滾至0snapshot／0documents；這不是只在寫入前
擋掉壞輸入。之後兩個同時 first imports 得到一個inserted、一個verified unchanged；
最終只有1snapshot／142documents。重複匯入全部 rows／UUIDs／rawJSON／imported_at 不變，
讀回typed documents 與原plan精確一致。缺漏／重複／changed payload／held input 都拒絕；
新測試庫內刻意製造stored header corruption與缺少child，reader/importer均拒絕而不修復。

在全新測試庫先匯入原有120synthetic canonical fixture 作比較基準；7張canonical tables
的每一列、ID／UUID／timestamp 前後完全一致，before/after row-snapshot SHA256 同為
`ed4be9dc736c8ac476ca5fd2a66b4f5e4e104ed25583c98e6fd8c355f60b2daf`。此 hash 包含本次動態
fixture timestamp，不是跨run固定dataset checksum。Actual fixture counts：product_variant120、
product_alias240、identifier120、provenance_record120、index_metadata1、product_search120、
product_embedding0。這些fixture僅写入新測試庫，不是寫入使用者工作資料庫。

25新增測試 PASS；full473tests PASS，唯一 warning仍是既有Starlette／AnyIOBlockingPortal
deprecation。RuffF/I、isolated strictMyPy on repository/supervisor、compile 與 frozenplan/
storedfinal integrity checks PASS。舊 source/data/config/API/identity/Dockerfile/compose/
canonical0001/final artifacts 未改，沒有新的 final collector run、模型重訓或 latency claim。
Raw [SQL report](../reports/human-knowledge-postgres-t49-2.json) SHA256 為
`3450185e2f8b6d97b5b39c3e563265080e8f11d5b8db988bfd28fd448c22c39d`；唯讀 `--check` PASS。
詳見[SQL證據](evidence/t49-2-human-knowledge-postgres.md)與[AI rubric](evidence/ai-evals/t49-2-postgres-storage.md)。

### 清理成果、未完成工作與下一步

本次建立的兩個容器與 internal network 已刪除，cleanup errors0、remaining owned resources0，
tmpfs測試資料已隨容器清除；舊 containers／volumes／images 保留。因此現在沒有一個已填入
142筆、可供日常查詢的永久DB，保留下來的是程式與可追溯報告。正式儲存／role permissions／
durability／optional runtime hydration／perquery SQL cost 尚未驗證，不能把 isolatedSQL PASS
解讀成正式RAG上線。依 Lite 更新任務、QA、decisions 與日誌，所有deliverables都在獨立repo。
下一步 T49.3 先 freeze 新storage profile／source／artifact／development-cost protocol，
不在已scored v4模組原地改寫，不重用final105questions做live selection/replay。
網站權限、約3,000真實資料與exactvariant evidence仍是獨立後續工作；本次授權沒有擴張。

## T49.3 規劃 — 人工知識 storage profile 與 development 驗證協議草案

Date:2026-09-14. Lite mode. Planningdelivery only; approvalfreeze/build/SQL/cost NOT RUN.

### 新執行內容與問題

前一步證明142筆人工知識可以在新隔離PostgreSQL完整保存，並且不改canonical rows；
測試庫已清除，還沒有讓查詢API使用這種來源。你在「下一步規劃profile／測試協議」的
交接後要求執行，因此本次交付限定的T49.3規劃草案，不推定新的DB操作／正式部署授權。
要解決的問題是：換人工知識儲存來源後，如何保證候選與正式答案不變、運作中資料庫
失效時如何拒絕回覆，以及哪些新增成本需要誠實量測。沒有捏造三份規格獨立確認或新輸出。

### 改動位置與理由

新增 `specs/human-storage-profile-development/` 的 requirements/design/tasks/review 與
`protocol-draft.json`，把profile、完整性／錯誤行為、版本綁定、199dev比較與成本步驟寫成
可驗收契約。新增[新手guide](HUMAN-STORAGE-PROFILE-GUIDE.md)解釋儲存來源和RAG計算的差別；
planning evidence／AIrubric、D49、README與上層task同步區分planning／freeze／implementation。
這次沒有修改產品Python、API、config、migration、原始資料或封存report；原因是新adapter
策略與協議需要先確認，不能把草案當成已批准實作。FullT49.3仍未勾選，僅T49.3-PLAN完成。

### 技術選型與從真實介面得到的設計限制

唯讀inspection確認現有API提供 `service_factory` hook，ResolverService constructor 可接
明確HumanKnowledgeCatalog與v4config。因此提議新增compositional factory，而不是修改
已scored service/config/api或monkeypatch舊global app。PostgreSQL只作人工snapshot儲存與
完整性來源，human候選仍用未修改castingidentity gate／hash192／RRF60／floor0.5／weight1.0。
不能因此稱為perquery SQLvector retrieval；canonical RAG仍唯一控制正式UUID、product、
status、confidence、policy／calibration，human RAG僅debug。顏色／輪圈／tampo仍需後續
release evidence，不能由casting family結果推定。

另一個實際限制是HumanKnowledgeV4Config固定oldmathprotocol SHA，不能把新storageprotocol
hash塞進同一欄位。草案將兩個protocol／newartifact references分開，保留原math參數與
oldsource/artifact的排除界線。T49.2repository固定142與disposableDBnameguard也不放寬；
新的readprofile只在另外確認的新隔離環境使用，沒有任意workingDB URL／latestfallback。
HTTPtitlemax500和直接human core512char／64pretokens等限制分開，不偷偷改公開API上限。

### 儲存／健康檢查方法的取捨

草案選擇啟動时建立cached142docindex，但在每次health／有效resolve前唯讀核對完整
selectedsnapshot。Startup-only hydration較省，但DB在啟動後斷線／被改／少文件仍可能
顯示healthy，不符合本次failclosed語意；header-only probe又無法發現childpayload被改。
因此提議SELECT-only application role、完整snapshot/source比對，失敗503且latch至restart，
不autoretry／repair／filefallback。代價是每請求SQL與network完整性工作、較嚴格availability；
HTTP成本要包含這些，不能只量memory核心。此方法仍待確認，沒有把它寫成已測功能。

10倍規模下fullsnapshot JSON／sourcevalidation／network成本會增長，應先依新協議量測
再改validation策略，不能提早宣稱3,000真實商品或高吞吐能力。Current142-only snapshot
合約也不能直接塞synthetic3000拿來當SQLscale結果。PerquerySQLvector／ANN／neuralindex
會影響admission／fusion與artifact，另案處理，不綑綁在保存資料這一步。

### 驗證協議草案與本次實際檢查

固定199devcases：168positive／4merge／7hold／20unrelated，新file／DB兩路各199一次性
correctness calls（無prewarmup／retry），原default另199nondebugreferencecalls。候選排序、
全部score／rank／type／ID／UUID／typedpayload／workcounters要一致，正式nondebug body
與default完全相同。這是已見過輸出的development資料，不是新holdout；草案誠實記錄
legacydev/final outputs viewed=true，newstorage outputs=false，不重跑final105或做參數搜索。
Raw先發布再score，失敗run保留。Cost另5startup/profile與199pairedHTTP/core samples，
3warmups/profile，nearest-rankp95；提出5000msstartup／150msintegrity／250msHTTP／25mscore
工程上限，需先批准封存，不是已測SLA或從新輸出倒推的門檻。

本次實際只有JSONparse／draftfalse-null狀態／199與142counts／11baseline sourcehash checks、
文件whitespace以及唯讀upstreamplan／T49.2／storedfinal integrity checks PASS。原有473tests
和SQLPASS是上一步證據，沒有重新包裝成新增profiletest；沒有profileadapter、role、DB、
retrieval或新latency／accuracy输出。Approvedspec／actualadapter manifest／runtimeimage欄位
維持null，protocol狀態 `draft_unapproved_not_executable`，不宣稱已freeze或可執行。
詳見[planning evidence](evidence/t49-3-planning.md)與[AI rubric](evidence/ai-evals/t49-3-profile-planning.md)。

### 下一步與未完成範圍

依spec-dev-loopLite先請owner確認新需求，再確認設計、任務與budgets，才建立approvedspec/
protocol與sourcefreeze；之後新file／DBadapter、完整性gate與新的隔離測試依HSP1–4分步做。
本次只送交草案，不做正式rollout或新DB寫入。T49.3fullimplementation／T49.4runtimepackaging/
closure、約3,000真實來源與exactvariant review都未完成。所有deliverables限於獨立Product
Variant Resolver repo，project log繼續保留原因、選型、scope與真實驗證，而不是只列已做事項。

## 2026-09-14 — T49.3 需求確認與設計交接（Lite）

Owner在需求說明後回覆「確認完成，請繼續執行」。本次執行將這個確認沉澱成可追溯的
[approval ledger](../specs/human-storage-profile-development/approval.md)，解決草案已送交、
但文件尚未區分需求已接受與整體實作尚未批准的問題。確認限定於 c197d0f 的需求文件
與其完整SHA-256；保留原文件bytes，不修改後再假裝仍是同一份已批准內容。

修改集中於新確認紀錄、protocol草案的requirements flag、tasks/review、README與教學指南。
沒有修改產品模組、migration、資料或舊測試證據。設計及任務／成本預算仍待分別確認，
protocol仍為不可執行草案，approved-spec、actual-source與runtime bindings保持null。
採用外部ledger而非覆寫需求版本，是為了讓後續freeze可以準確指回使用者實際確認的內容。

本次設計交接說明新file／PostgreSQL來源如何在啟動時建立同一份142筆記憶體索引，
以及每次有效請求前完整唯讀核對snapshot的取捨。完整核對比只看連線或header昂貴，
但能發現運作中斷線、缺文件或payload改動；HTTP成本必須包含它。原API不切換預設，
canonical仍控制正式答案，human仍只提供debug證據，舊檢索數學參數不因storage變更而改動。
這些是待確認的設計，不是已實作功能；尚未增加DB角色、SQL run、199筆新輸出或效能數字。

驗證僅核對已批准需求SHA、JSON的單一確認flag及false/null未執行界線，以及git whitespace
檢查；結果PASS。不重跑產品測試、SQL或final105，既有473 tests不當成本次新增功能證據。
下一步先取得設計確認，再送交任務／預算確認，之後才可執行HSP-1的封存工作。
Full T49.3/HSP1–4/T49.4仍未完成，所有本次文件都保留在獨立專案資料夾。

## 2026-09-14 — T49.3 設計確認與任務／成本交接（Lite）

Owner在設計說明後回覆「確認 繼續下一步」。本次把確認綁定到7a90be0的design文件
SHA-256，補入[確認ledger](../specs/human-storage-profile-development/approval.md)，
保留已確認的需求及設計bytes。這解決需求已批准但設計狀態仍停留WAIT的追蹤落差，
並且沒有把「下一步」擴大成全部任務、成本預算或新SQL環境已獲批准。

修改僅涉及protocol的design flag、ledger、tasks/review、README、教學指南與AI rubric。
教學指南補充四個任務順序及成本計時界線，讓不熟程式的owner知道先封存再實作、
模擬API測試與真實SQL證據不同，以及為何完整HTTP耗時不能用純記憶體檢索耗時代替。
沒有新增產品模組或migration。整體G1仍等待第三份任務／預算確認，execution bindings
仍null，新輸出與執行flags仍false；HSP1–4及Full T49.3仍未勾選。

方法與技術棧維持已確認設計，不重新挑選檢索模型。成本協議保留每一路5個獨立程序
初始化樣本、HTTP／core各3次預熱及199樣本、單worker循序測量，及5000／150／250／25ms
四個p95門檻。門檻是待批准的本機工程上限，不是已測SLA；特別說明5個啟動樣本的
nearest-rank p95就是最慢樣本，避免讓小樣本看起來像可靠的長期延遲統計。成本預熱
不混入199題零預熱的正確性比較，也不重跑挑選成功結果。HSP-3新隔離SQL run仍需
另外明確授權，既有測試庫或volume不在scope內。

實際驗證只有JSON確認界線、原需求／設計SHA未變與git diff whitespace檢查PASS。
本次没有新測試套件、SQL、檢索或效能輸出，既有473 tests仍只屬上游證據。下一個
最高價值步驟是確認任務／耗時預算，然後執行HSP-1封存，不是立刻建立工作資料庫。
所有文件仍限於Product Variant Resolver資料夾，project log保留原因、取捨與未完成項。

## 2026-09-14 — HSP-1 開始實作：封存已批准的輸入，而非宣稱API整合完成

Owner在任務／耗時上限說明後指示「開始執行」。本次完成第三份確認，通過限定於新
storage profile的G1，並實際執行第一個任務。原本只有草案與口頭確認，尚不能確定日後
測試用的是哪份規格；現在新增8檔案封存，保存原需求、設計、任務、協議草案bytes，
以及批准紀錄、新protocol、宣告profile與manifest。它綁定26個既有輸入指紋，不新增
142筆副本或商品UUID，也沒有開始199題實驗／SQL run。參見[實際驗收證據](evidence/t49-3-input-freeze.md)。

新增`scripts/freeze_human_storage_development.py`負責明確Git版本的規格讀取、SHA核對、
衍生批准協議、exclusive publication與check；新增test文件以暫存資料測資料改動、
缺檔／多檔／symlink、改規格或producer、拒絕覆寫及pending狀態。程式選用Python標準庫，
沒有安裝SQL或模型依賴：這一步只需Git與檔案驗證，用資料庫工具反而增加範圍與憑證風險。
先提交producer為448f9c0，再產生封存，讓manifest能指回真正已提交的產生程式。

設計沒有重新選型。保留舊math protocol，另建storage protocol；approved_spec hash是
四份commit/path/SHA bindings的canonical JSON指紋，原文件各自也有byte SHA。
選Git snapshot而非改寫所有draft標頭，是為了留下owner實際確認內容。選exclusive
publication而非覆寫既有結果，是為了留下失敗或變動痕跡；代價是程序被殺可能留partial
directory，必須由check拒絕，不能宣稱crash-atomic或OS強制不可寫。
新profile仍只是合約，actual adapter/import manifest及image IDs都null，ready=false；
後续HSP-2需補完並封存全imported sources/runtime，不能沿用此次不完整runtime binding。

實際新增16項測試PASS；Ruff F/I與isolated strict MyPy PASS，freeze／check均PASS。
第一次完整pytest未帶PYTHONPATH，488PASS／1FAIL：既有report測試的子程序找不到套件。
沒有改產品碼或測試assertion，補上既有執行方式`PYTHONPATH=src`後489PASS，保留一項
Starlette／AnyIO既有deprecation warning。這是修正測試呼叫環境，不是重跑真實實驗挑結果；
兩次結果都寫入evidence。14.22秒是測試套件耗時，不當成profile latency。
既有src、migration、config、核心資料與舊supervisor差異為空；沒有新增DB或憑證。

決策D50只接受input freeze，D49 runtime安全／成本尚未驗證。HSP-1勾選完成，但Full
T49.3、HSP2–4與T49.4不勾選。下一步新增profile loader、唯讀完整性gate與組合式API入口，
先以單元／模擬測試驗證；HSP-3真實SQL隔離環境仍須另外明確批准。所有產物與日誌
都位於Product Variant Resolver獨立repo，沒有把root agent設定納入推送。

## 2026-09-14 — HSP-2：接上可選儲存安全門，但不把fake DB說成PostgreSQL證據

Owner在HSP-1完成、下一步明確標為HSP-2後要求「執行下一步」。此前只有固定的協議，
API還不能選擇file／PostgreSQL snapshot，也不能在啟動後偵測來源失效。本次新增獨立
storage profile與app入口：啟動驗證完整142筆並建立既有v4記憶體索引，每個health／
有效resolve再完整唯讀核對來源；一旦失敗便清空app service，直到process restart都503。
原`api:app`仍正常ready，新entrypoint沒profile則not ready，沒有默認切換或舊路fallback。

`human_knowledge_storage_profile.py`修改的是儲存合約邊界：strict/no-duplicate JSON、相對
contained paths、storage/math protocol分離、plan與source SHA、兩種mode、外部URL env及
runtime/mock狀態；Postgres只接受既有`pvr_t49_2_<12hex>`guard。它透過既有repository
的whole-snapshot reader，不新增寫入／修復方法。`human_knowledge_storage_app.py`修改的是
組合邊界：subclass先probe再`super.resolve`，debug在既有timing/model maps增加storage
版本，nondebug canonical body不增加欄位。Health wrapper增加獨立storage dependency，
不把human SQL冒充原`database`（canonical backend）。舊API/service/config/v4/data未修改。

選subclass+factory是因為既有API已提供service_factory、ResolverService已接受明確human
catalog/v4 config；直接改凍結模組較短，卻會破壞先前source-bound證據。選每次完整142
核對而非啟動一次／只看header，才能發現斷線與child payload變動；代價是SQL/network
成本與較嚴格availability，留給HSP-4按已批准門檻實測。沒有用SQL做TopK或改0.5／1.0／
hash192／RRF60，Dual RAG仍由canonical決定正式答案，human只在debug提供casting證據。

測試選private fake repository，使HSP-2能驗證呼叫與故障語意而不偷啟動DB。42項adapter/API
測試後，來源封存測試共55PASS；完整套件544PASS，Ruff/MyPy/compileall與只讀上游checks
PASS。過程保留三類問題：pytest保留參數造成collection error；短`Chevy Nomad`不保證
matched的錯誤測試假設（換成既有明確catalog case，產品碼未改）；第一次source generator
只hash工作檔，50PASS/4FAIL揭露未綁同commit，後改為42檔逐一比對Git bytes。
Starlette/AnyIO既有deprecation仍1項。這些是開發測試，不是199題新結果或latency。

最初commit5d9e2f3的candidate1在review時又發現health缺獨立versioned dependency；依不覆寫
原則保留並加SUPERSEDED說明。補強後commit bd2a838產生accepted candidate2，adapter
manifest`93a8b631…`、42inputs、ready=false、runtime images=null。此決策改變的是「來源
候選版本」，不改需求、數學或輸出權限。HSP-2因此完成，但HSP-3真實SQL仍未授權：
SELECT-only role拒寫、199file/DB逐筆parity、完整fault matrix與runtime image還沒驗證；
HSP-4成本也未量。下一步先向owner說明新的隔離環境與動作，再取得明確SQL run指示。

所有程式、tests、兩個candidate與敘述證據只在Product Variant Resolver repo；沒有加入
root agent設定、憑證、資料庫URL或現有volume。3,000真實資料及顏色／輪圈／tampo精確
variant仍屬後續來源審查，不從本次casting-level storage結果推論。

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

## 2026-09-15 — HSP-3：證明 file 與 PostgreSQL 儲存等價，保留三次測試基礎設施失敗

使用者在上一階段已被明確告知下一步是另建隔離SQL環境後，要求「繼續執行下一步」，因此
本次只執行HSP-3，不擴張到HSP-4成本測試或正式部署。問題不是再改善檢索準確率，而是此前
只有private fake repository，尚未證明同一份142筆human knowledge放在JSON file或真實
PostgreSQL時會得到相同結果。現在可觀察的成果是：固定199題的兩路human候選與work
counters逐筆完全一致，正式canonical body也與原default API一致；真實reader只能SELECT，
斷線／內容破壞會503並鎖住到restart。Dual RAG權限未改，human仍不能填入正式UUID答案。

程式修改集中在四個新HSP-3 scripts與一個test。`freeze_human_storage_hsp3_run.py`先固定每次
執行的source commit、兩個runtime profile、development pack、protocol、image ID及一次性
resource名稱，避免先看到結果再改條件。`run_human_storage_profile_sql.py`只建立帶本次label的
internal network、tmpfs PostgreSQL和read-only runner，不使用compose／host port／volume；
密碼每次隨機產生，只進短期container environment，錯誤報告只保存stderr hash。
`verify_human_storage_profile_sql.py`先migration及匯入canonical120+human142，再建SELECT-only
role，交錯執行199組file／DB health+resolve與199個default reference，最後注入10個啟動故障、
4個啟動後故障、5個無效HTTP和4種寫入。`score_human_storage_profile_sql.py`只讀已發布raw，
不呼叫SQL或retrieval。這個分離是為了滿足raw-before-score，而不是單一script邊跑邊挑結果。

方法選擇延續PostgreSQL16、SQLAlchemy2、Alembic與既有whole-snapshot reader，因為HSP-3
要隔離「storage」變因；沒有改成SQL TopK／pgvector ANN，否則同時改了candidate admission與
數學，無法知道差異來自儲存還是模型。每個有效health／resolve完整讀142筆，能看見child
corruption，但成本較高；HSP-4才會按已固定的5次startup、3次warmup與199 HTTP/core樣本評估，
本次25.6秒總執行時間不能當作latency。相同request ID及奇偶交錯順序降低固定順序偏差；
21個空候選保留，沒有只報好看的178筆。3,000筆、顏色、輪圈、tampo與release identity仍未驗證。

執行過程的決策有三次窄化，全部保留而沒有覆寫成一次成功。Run-v1在建立role時發現
PostgreSQL DDL不能用`$1`綁password；改成只接受48位hex後安全嵌入DDL。該失敗trace曾回顯
已隨DB刪除而失效的短期密碼，基於密鑰零落地刪除敏感raw，留下明示redaction的sanitized
失敗紀錄，後續supervisor只存stderr SHA。Run-v2的missing-snapshot fixture先刪header，
被FK23503正確拒絕；改為children先刪。Run-v3直接寫錯namespace，被CHECK23514拒絕；
改成bootstrap暫時drop該human-table constraint、寫錯值讓app驗503，再恢復值與constraint。
每次修改先commit，再另建run-v2/v3/v4 freeze；每組container/network都確認cleanup errors=0、
remaining owned resources=[]。這些是故障注入方法修正，沒有改產品碼、資料或正確性門檻。

最終run-v4 raw SHA`19301513…0454`先發布，之後evaluation SHA`a6fdcb34…0895`才產生，
exact parity199/199；case組成168positive/4merge/7hold/20unrelated，兩路各21空候選、262個
候選總數，所有per-case health=200及request ID一致。Reader attributes為LOGIN true，
super/inherit/create-role/create-db false，兩張human tables只有SELECT；四種寫入均SQLSTATE42501。
10startup及4post-start故障皆503，修復來源後同process仍503；無效HTTP為400/415/422且probe0。
七張canonical table前後SHA同為`1d7b7f8a…bc172`。Linux aarch64、Python3.12.14、
PostgreSQL16.14、SQLAlchemy2.0.52、Alembic1.20.0、psycopg3.3.5、runner UID100。
Focused59、完整548測試PASS，Ruff F/I/format、strict isolated MyPy與compileall PASS；只剩既有
Starlette／AnyIO deprecation warning。詳細證據在`docs/evidence/t49-3-storage-profile-sql.md`。

HSP-3因此完成，但Full T49.3仍不能勾選：HSP-4尚未量啟動、每次完整snapshot revalidation、
真實loopback HTTP及core成本，也沒有3k/concurrency/durability/production證據。下一個最高價值
動作是先依凍結cost protocol檢查HSP-4執行條件與資源界線，再決定是否啟動新的測量環境。

## 2026-09-15 — HSP-4：量出完整snapshot安全門的成本，完成限定T49.3

### 背景、問題與可觀察結果

使用者在HSP-3完成且下一步已明確說明為HSP-4後要求「繼續執行」。先前已證明file與真實
PostgreSQL保存同一142筆human knowledge時，固定199題的檢索結果完全相同，但「每個有效
request都重讀完整snapshot」的時間成本仍未知。因此這次不是再調Dual RAG準確率，而是依
已批准且預先封存的工程上限，量profile初始化、完整性核對、真實HTTP與純human retrieval。
最後八個file／PostgreSQL p95 gate全數PASS；bounded T49.3因此完成，原default API仍未切換，
T49.4封裝／rollout、3,000筆與顏色／輪圈／tampo release identity仍保持未完成。

### 程式修改與原因

新增的四個HSP-4 scripts把「固定考卷」「建立一次性環境」「收集raw」「離線評分」分開。
`freeze_human_storage_hsp4_run.py`先綁implementation commit、兩個profile、199題pack、cost
protocol、image IDs及owner resource名稱，避免看到速度後改條件。`run_human_storage_profile_cost.py`
只建立帶`pvr.t49-4.owner`label的internal network、tmpfs PostgreSQL與read-only runner，密碼只在
執行時隨機產生；完成後只按精確label與ID清理。`verify_human_storage_profile_cost.py`建立
SELECT-only reader，取兩路各5次新process初始化、3次HTTP／core預熱與199次交錯正式樣本，
並保留每筆duration、status、error、abstention。`score_human_storage_profile_cost.py`不再碰DB
或HTTP，只驗合約／數量後用nearest-rank套固定門檻。新test覆蓋percentile、PASS／FAIL門檻、
樣本數、隔離參數與不得依賴缺失`httpx`。產品retrieval、API、資料、migration及門檻未修改。

### 技術選型、替代方案與代價

測量使用真實Uvicorn loopback而非TestClient，因為HTTP預算需包含ASGI server、序列化與client
解析；core則用已初始化service及預先抽取signals，刻意排除SQL／integrity／canonical／HTTP，
讓兩個數字回答不同問題。file與PostgreSQL按奇偶交錯，避免固定「永遠先file」的順序偏差。
nearest-rank不用插值；5個startup的p95等於最慢值，計算保守但樣本小，不能冒充長期SLA。
資料庫沿用PostgreSQL16、SQLAlchemy2、Alembic與whole-snapshot adapter；沒有改成SQL TopK或
ANN，因為那會同時改候選數學而破壞storage-only比較。代價是每個有效request完整讀142筆，
PostgreSQL HTTP p95比file多約7.52ms，但42.77ms integrity與46.16ms整體HTTP仍低於原門檻。

### 決策改變與觸發證據

Run-v1在任何計時樣本產生前停止。原因不是速度不合格，而是固定runner映像有Uvicorn卻沒有
`httpx`，module import時即失敗，原supervisor只得到空stdout的JSONDecodeError。v1 raw仍保留，
兩container與network全數清除，且沒有密碼／DB URL。沒有臨時下載套件或換一個較有利的映像；
改用Python內建`urllib`維持相同real-HTTP計時邊界，並讓supervisor對空／非法stdout產生結構化
runtime_error及stdout/stderr SHA。修正先commit`31a97e4`，再建立獨立run-v2 freeze`ff5b7d4`。
兩版image、資料、protocol與門檻不變；v2不是看到慢結果後的重跑，也沒有timed retry。

### 驗證證據

Run-v2 raw SHA`78e9eb938ff3615ebc3cf51418e9c06c463cf397a4f6138526863a0ced6c87ed`
先以unscored發布，包含10個startup、12個warmup、398個HTTP與398個core正式結果；HTTP／core
error均為0。之後evaluation SHA`af5ff062fb1f269f3b07ab27c9059a9d9ad31a4487f5ac131aadf724805dcccc`
才評分。file／PostgreSQL p95依序為：startup271.142／300.175ms（上限5000）、HTTP38.645／
46.163ms（250）、integrity34.204／42.773ms（150）、core2.311／2.306ms（25），八項PASS。
環境為Linux arm64、Python3.12.14、PostgreSQL16.14、Uvicorn0.52.4、SQLAlchemy2.0.52、
Alembic1.20.0、psycopg3.3.5、UID100。reader只有LOGIN+兩表SELECT，無super/inherit/create
role/database。兩containers與internal network已刪除，cleanup errors與remaining均空。

聚焦79項測試PASS。第一次完整pytest未帶`PYTHONPATH=src`，既有evaluation子程序因找不到
package而1FAIL；沒有改碼或assertion，依專案既有方式補`PYTHONPATH=src`後552/552 PASS。
changed-file Ruff F/I、strict isolated MyPy與compileall PASS，仍有一項既有Starlette/AnyIO
warning。全repo Ruff另列54個本次以前的import-order債務，沒有趁此任務大量改無關檔案。

### 未完成、風險與下一步

這份PASS只涵蓋本機ARM64、142份文件、單worker、concurrency1；沒有測throughput、多worker、
durability、production SLA或10倍／3,000筆完整snapshot成本，也沒有驗證來源權利與release-level
顏色／輪圈／tampo。下一個最高價值動作是T49.4：把已通過的可選profile整理成可操作的
runtime packaging/runbook，明確決定仍維持opt-in或另行批准rollout；不能因T49.3通過就自動
更改default API或建立長期本機資料庫。

## 2026-09-15 — T49.4：把可選file profile做成可重現的Docker服務

### 背景、問題與可觀察結果

使用者在HSP-4完成、下一步已明確指出為T49.4後要求繼續執行。當時程式已證明file與
PostgreSQL保存相同142筆human knowledge會產生相同候選，也量過本機成本，但一般使用者仍
沒有一條被驗證過的方式把storage-gated app啟動起來。這次新增的是可選runtime package，
不是新的Dual RAG演算法或資料。現在操作員可透過獨立Compose profile啟動file-backed服務；
缺profile會停止，正常服務health會顯示固定storage version，四組非debug正式回應與default
reference完全相同。原本API的Docker路徑、canonical權限與預設行為沒有被切換。

### 程式修改與原因

`Dockerfile.human-storage`與專用`.dockerignore`建立一個能執行strict profile loader的最小映像，
只帶`src/data/config/ui`、必要scripts和被遞迴驗證的selection/plan證據；這樣後來新增一般QA
report不會無意改變映像。`docker-compose.human-storage.yml`同時提供default reference與只有
明確`--profile human-storage`才選到的storage service，將profile以read-only bind掛入，並保留
nonroot、read-only root、tmpfs、loopback和single worker界線。

`freeze_human_storage_runtime_package.py`在看runtime輸出前，將implementation commit、確切
image ID、profile SHA、來源與封裝檔hash寫入不可覆寫的versioned package；`verify_...py`則建立
唯一Compose project，先測缺profile，再測health/debug／四筆正式回應／Docker inspect，最後
只清理由owner label辨識的資源。新增七項static tests檢查opt-in、allowlist、freeze與cleanup
合約。規格、review、runbook、QA evidence及AI rubric同步建立，避免只有程式沒有接手說明。

### 技術選型、替代方案與代價

採用獨立Dockerfile/Compose而不是修改歷史封裝，因為IBR-T5已把原三個檔案的SHA當作驗收
證據。外部profile不能直接烘進自己所綁定的image，否則會形成「要先知道image ID才能build
該image」的循環，所以先build再exclusive freeze，runtime只讀掛載。選擇file mode是因為它
不需要放寬目前只允許一次性DB名稱的guard，也不需要發明正式secret、migration/import、backup
與volume生命週期。代價是這一步沒有帶來長期PostgreSQL服務，而且顯式allowlist在協議新增
間接證據時必須維護；這是可稽核性換來的維護成本。

### 決策改變與觸發證據

最初曾直接修改`.dockerignore`、`Dockerfile`與`docker-compose.yml`加入storage service；聚焦
回歸測試立刻以IBR-T5封裝SHA漂移失敗，因此三檔完整還原，改成三個專用新檔。這不是單純
換檔名，而是保留歷史runtime證據與不改default路徑的必要決策。

第一個專用映像`923da9b4…8617`及v1 freeze也沒有被包裝成成功。缺profile測試正常拒絕，
但真正startup因v4 math protocol遞迴要求`family-retrieval-development-v1/selection.json`而失敗；
profile直接列出的檔案完整，間接證據卻沒進image。沒有關掉遞迴SHA檢查或粗暴複製所有reports，
而是加入確切selection/plan與兩個producer，再以新commit重build成`d8ccf54d…0e718`並另建v2
freeze。v1 sanitized failure仍在repo，能回答「為何現在image需要那些看似不像產品碼的檔案」。

### 驗證證據

v2 manifest/profile SHA為`b89dfbc4…624`/`a51d3112…980a`。隔離Docker report先於本次收尾文件
產生，SHA`bac44242…761c`、verdict PASS：missing profile exit1且path未被建立；兩service health
200；四個canonical comparison均200/200且內容hash一致；debug有固定storage version/SHA及
integrity timing。Docker inspect確認兩container都是確切image、user`pvr`、read-only root，
storage profile mount為RO，host僅`127.0.0.1:18080/18081`。cleanup errors與remaining皆空。

完整`PYTHONPATH=src .venv/bin/pytest -q`為559/559 PASS，聚焦package/storage/API/v4 closure為
71/71 PASS；兩個scripts的strict isolated MyPy、compileall、changed-Python Ruff F/I和Compose
config均PASS，仍只有既有Starlette／AnyIO deprecation warning。一次QA命令誤把Dockerfile交給
Ruff當Python而得到78個syntax findings；適用的Python-only Ruff隨後PASS，Dockerfile也已成功
build及實際啟動，因此該次結果是命令選檔錯誤，不是隱藏的產品失敗。

### 未完成、風險與下一步

T49.4只涵蓋本機ARM64、142 documents、file mode、one worker及循序smoke。沒有PostgreSQL
deployment、正式TLS/proxy、concurrency/durability/SLA或3,000筆成本，也沒有證明外部來源權利
或顏色／輪圈／tampo的release-level identity。下一個最高價值功能工作是VAR-PLAN1：先建立
100筆來源列的欄位證據審查計畫，保留unknown/conflict，再提出小批人工review；不能把目前
casting storage PASS直接升級為variant資料已完成。

## 2026-09-15 — VAR-PLAN1：把100筆來源列拆成可逐欄審查的證據，而不是直接叫作版本

### 背景、問題與可觀察結果

使用者在T49.4完成並被告知下一步是VAR-PLAN1後要求繼續。專案此前已能辨識casting family，
也能保存142份human knowledge，但同一casting的顏色、輪圈、tampo和包裝差異仍沒有release
truth。這次讀取現有100筆2025來源，確認100筆color全是null、wheel/tampo欄位不存在；45筆
只有`2nd Color`、`3rd Color`或`Zamac`文字提示。因此可觀察成果是完整100筆欄位證據plan，
不是100個已驗證variant：每筆仍held、沒有canonical UUID或variant equivalence，並提出一個
4families/11rows的第一批人工review工作量。

### 程式修改與原因

新增`plan_release_field_evidence_review.py`，在本機將normalized100、cross-catalog review100與
最終53-family queue以`source_record_id`做嚴格一對一join。每列得到另一個deterministic
observation ID，避免把來源列ID誤當產品identity。十三個欄位各自保存raw value、
`observed_unverified/unknown`狀態、來源JSON pointer及未來允許的人類狀態；variant note只照錄，
不解析成顏色。`--run`只能發布到不存在的資料夾，`--check`從三個來源重新產生並逐byte比較。

新spec定義EARS需求、資料權限、批次選擇及錯誤界線；JSON計畫保留100筆機器可驗證資料，
Markdown讓初學者能先看差距與批次。九項test覆蓋100筆membership、null、all-held、ID分離、
完整family批次、不可覆寫／漂移、來源刪列及無network/DB client。review、evidence、AI rubric、
架構決策、README與本日誌同步更新，因為「如何知道這個值能不能相信」是此功能的主要產物。

### 技術選型、替代方案與代價

採逐欄evidence envelope而非只有一個row-level confidence，因為series可能有來源而color未知，
不能讓整列看起來同樣可信。選用observation ID而不產生variant ID，因為觀察一列只證明來源
存在；兩列都缺wheel也不能推出同一版本。第一批使用complete-family greedy pattern coverage，
最多5 families/15 rows，讓reviewer同時看到same-casting siblings並涵蓋create/merge/hold、
series差異、Zamac與無note情境。代價是這批刻意多樣，不是隨機抽樣，不能估計variant accuracy。

沒有用spreadsheet手填固定清單，因為那難以重現來源hash與遺漏；沒有先爬casting pages，因為
目前source-specific rights/access仍未重新確認。JSON在100筆規模最簡單，10倍時可能需要分頁或
資料庫，但現在先驗證review工作流，避免替尚未證明可用的流程過早做基礎建設。

### 決策改變與觸發證據

第一次未提交的plan顯示第五個family重複Lamborghini Huracán Sterrato。根因是selector將加入
`new_coverage_at_selection`後的字典，拿去和原candidate做整個字典相等比較；shape不同便被當成
尚未選過。錯誤兩個產物被精確刪除，selector改以immutable`family_review_id`集合追蹤，test要求
family ID unique。進一步發現第五組沒有增加任何風險覆蓋，因此不再為了湊到5組而選；當三種
decision與所有資料pattern已覆蓋就停止，最終得到較小的4families/11rows，來源與欄位規則不變。

### 驗證證據

最終JSON/Markdown SHA為`f470d731…675a`/`ae3ffe3a…c43f`，綁定三個輸入SHA
`e5e0384a…b9a6`,`72029287…c4e`,`989bc914…e4d8`。計數為100 source/100 observation/53 families；
color/wheel/tampo/edition/packaging unknown各100，literal variant note45；held100，canonical UUID、
variant equivalence、owner field decision皆0。第一批包含Lamborghini Huracán Sterrato3、Subaru
BRZ3、Nissan Skyline 2000GT-R LBWK3及'87 Audi quattro2。

聚焦9項與完整568項測試PASS。changed-file Ruff F/I、strict MyPy、compileall與artifact`--check`
PASS；只有既有Starlette／AnyIO deprecation warning。測試還以刪成99筆的暫存來源確認planner會
fail closed，並確認script沒有requests/httpx/urllib/SQLAlchemy/psycopg/Docker client import。

### 未完成、風險與下一步

沒有任何欄位被owner確認，也沒有檢查目前Fandom授權／robots／API可用性、讀新頁面、處理圖片、
寫SQL或改runtime。這不是100 verified variants，更不是3,000產品進度。下一個最高價值動作是
owner逐欄審查batch01的11筆：每個非null值要綁文字證據，無法證明保持unknown，有歧義標
conflicted，並分別決定same release/different release/unresolved。完成這個人類authority事件後，
才能決定是否建立append-only decision artifact；VAR-PLAN2遠端收集仍須另行確認rights與budget。

## 2026-09-15 — VAR-REVIEW1-PREP：把11筆資料變成owner真正能逐項回答的審查表

### 背景、問題與可觀察結果

使用者在VAR-PLAN1完成並被告知下一步是審查11筆後要求繼續。上一階段只決定「先看哪四個
families」，但plan.json有100筆×13欄，並未將過去research中的文字證據、每列差異與需要回答
的same/different/unresolved問題放在同一畫面。本次可觀察成果是batch01 packet：4families、
11rows、10個within-family pairs、143個欄位決定slot，以及一份全部空白的owner decision
template。它仍標示owner decisions0、canonical changes0、all rows held，沒有替使用者簽核。

### 程式修改與原因

新增`prepare_release_field_review_batch.py`，先驗VAR-PLAN1固定SHA與4/11 membership，再讀
normalized source、priority-1 evidence、priority-2 batch01與batch04 research。preparer將過去
family證據統一標記`casting_family_only`，逐列保留toy/collector/year/series position/variant
note/source markers及五個unknown physical fields。只有已封存摘要明確點名toy number的文字才
進入`candidate_pending_owner_review`；程式以exact publisher/URL/observed claim驗drift。

輸出四檔：`packet.json`保存機器可驗證證據，`owner-review.md`為新手表格，
`decisions.template.json`列出11×13欄與10個pair問題，`manifest.json`固定來源與三個主artifact
SHA。`--run`拒絕覆寫、`--check`逐byte重算。11項測試覆蓋membership/nulls/scope/claim白名單/
pairs/pending template/manifest/drift/changed plan與無network/DB client。spec、QA review、evidence、
AI rubric、roadmap、decision和本日誌同步更新。

### 技術選型、替代方案與代價

決策模板與證據packet分檔，是為了讓「機器整理了什麼」和「owner同意什麼」永遠可區分；若直接
在packet填預設答案，空白也可能被誤讀成默認同意。每個三列family產生三個pair、兩列family
一個pair，總計10題；不只問「這family有幾個variant」，因為那會跳過哪兩列相同的關係證據。

沒有重新開網頁。既有research已留下可歸屬文字，足以製作問題但不等於目前source rights或
真實欄位再次驗證。明確protocol只接受三個row claim，雖比通用NLP不靈活，卻避免從URL、series
或關鍵字自行杜撰。10倍資料時手工Markdown會太慢，未來可做UI；目前先確認決策契約是否讓owner
看得懂，避免先建大系統再發現問題問錯。

### 決策改變與觸發證據

Nissan HYX54的來源URL帶`metalflake-blue`，但凍結的`observed_claim`只明確支持toy、2025、
HW J-Imports與Tooned tool。原本可把URL視為顏色線索，但這與既有「不得從filename/URL推顏色」
邊界衝突，因此packet加入`explicit_non_claim`並維持color unknown。Subaru HYY12雖有`2nd Color -
Zamac`且human family也有Zamac label，兩份證據只因casting重疊，沒有row-level join authority；
所以整個Subaru family沒有row-specific claim。這些窄化降低自動填值數量，但保留真實證據強度。

### 驗證證據

packet/Markdown/template/manifest SHA為`2e2adee3…00b2`,`08bd164a…8e69`,`bc01138a…3724`,
`6957176f…5c63`。計數：4families、11rows、10pairs、3candidate claims、0owner field/pair
decisions、0canonical UUID。candidate只涵蓋HYW93 Lamborghini2025 release、JBC35 Audi2025
Super Treasure Hunt、HYX54 Nissan2025 J-Imports Tooned；三者狀態仍pending。

聚焦11與完整579項測試PASS，Ruff F/I、strict MyPy、compileall與exact artifact check PASS，
只剩既有Starlette／AnyIO warning。changed-plan測試把batch family count改成3後確認fail closed；
manifest測試逐一重算三個artifact SHA。

### 未完成、風險與下一步

這一步沒有owner field decisions，無法勾選VAR-REVIEW1。current rights、網站內容、圖片、顏色、
輪圈、tampo、release equivalence與canonical promotion都未驗證。下一步必須由owner閱讀
`owner-review.md`：先逐family判斷三個candidate claims是否接受，再為10個row pairs選
same_release/different_release/unresolved並附理由。若owner希望先採最保守安全狀態，可將缺乏
row-specific證據的欄位保持unknown、關係保持unresolved；但這仍必須由owner明確確認，不能由
preparer代簽。確認後才建立不可覆寫的decision artifact；VAR-PLAN2仍不是自動下一步。

## 2026-09-15 — VAR-REVIEW1 decision01：只記錄owner確認的Lamborghini範圍

### 背景、問題與可觀察結果

上一輪最後以明確問題詢問owner是否接受Lamborghini保守審查：只確認HYW93的casting/toy/
2025，三個toy numbers視為不同release，所有physical fields維持unknown。owner緊接回答
「繼續下一步」。本次將短回答視為該問題的同意，但不擴張成整個batch。現在可觀察到一個
packet-SHA-bound decision event：3 confirmed fields、15 unknown physical fields、3 different-release
pairs、canonical changes0；Subaru/Nissan/Audi仍pending，batch進度1/4。

### 程式修改與原因

新增read-only`validate_release_field_review_decision.py`，以原packet與manifest為authority，驗
event的owner question/response/scope/time、family membership、required fields、confirmed value是否
等於raw或candidate evidence、無支持physical field是否unknown、所有pair是否完整、reason/
evidence是否存在及summary能否重算。validator不寫檔，避免驗證工具自己改authority artifact。

`decision-01-lamborghini.json`保存原問題與`繼續下一步`原文，明確列出不批准的三個families、
source access與canonical promotion。18個required field decisions由HYW93三個已支持欄位，加上
三列各五個physical unknown組成；其他source-observed欄位保持未確認而非默認接受。新增10項測試
涵蓋正常事件與packet SHA、canonical flag、grounding、缺field、缺pair等篡改失敗。spec進度、
QA/evidence/rubric/roadmap/README/decision與本日誌同步回寫。

### 技術選型、替代方案與代價

採用一family一append-only event，不直接填滿可變的整批template，因為owner正在逐組學習與確認；
這可保留每次對話的真正授權範圍。短答可以要求重講完整內容，語意最明確但會在剛問完精確問題後
增加不必要摩擦；也可以當作整批批准，卻明顯越權。因此選擇保存question+response+窄化interpretation，
讓reviewer日後能判斷這個推論是否合理。

confirmed value只能等於packet raw或candidate value；不是靠任意reason補一個新值。所有三個pair
設different release，是owner接受上一輪已明說的保守建議，依據是三個不同toy-number source rows
和base/2nd/3rd release markers；這不代表知道它們的顏色。代價是其他21個Lamborghini來源欄位仍
只是observed-unverified，但這比一次把整列全部升格為人類真相更誠實。

### 決策改變與觸發證據

沒有把`Red Edition`複製成color或edition。HYY45的color/edition各自unknown；JBB86的`3rd Color`
也只支援它是另一個release marker，不支援物理顏色。事件scope完成的定義從「39欄全部人工
confirm」窄化為「所有row-specific candidate fields、所有physical unknowns、所有family pairs」；
其餘欄位可保持source observation。這符合owner實際確認內容，也避免杜撰未問過的決定。

### 驗證證據

Decision event SHA`b05c52842626b2c9dfadc66901dd6544ce237a7f7a010ce25611facc3475e5ef`，
綁定packet SHA`2e2adee3…00b2`。Validator輸出PASS：family`174efb…`、fields18、pairs3。
confirmed為casting name`Lamborghini Huracán Sterrato`、toy`HYW93`、year`2025`；unknown15；
different release3；same/unresolved/conflicted/rejected全0。

聚焦10與完整589項測試PASS，Ruff F/I、strict MyPy、compileall、CLI validation PASS，只有既有
Starlette／AnyIO warning。五種tamper cases全部fail closed，validator也沒有network/SQL/write path。

### 未完成、風險與下一步

VAR-REVIEW1仍未完成；進度1/4。Lamborghini的color/wheel/tampo/edition/packaging仍未知，沒有
canonical UUID。下一個owner問題是Subaru BRZ：HYW99、HYY12、JBB55是否應視為不同release；
`2nd Color - Zamac`能否只確認HYY12的Zamac finish，還是因family-level human evidence無法安全
對應該row而繼續unknown。為遵守authority邊界，必須先向owner呈現保守建議再記錄decision02。

## 2026-09-15 — VAR-REVIEW1 decision02：確認Subaru字面variant note，不推論實體顏色

### 背景、問題與可觀察結果

在Lamborghini完成後，我們把Subaru BRZ的保守審查結果逐項說明，並以「你是否確認採用這個
Subaru BRZ審查結果？」向owner取得明確回答「是」。本次只把這個回答解讀為Subaru範圍的核准，
沒有延伸到Nissan、Audi、canonical promotion或新的網站存取。現在batch01有2/4 families完成：
Subaru事件確認1個字面欄位、保留15個physical fields為unknown、將3個row pairs判定為不同release，
且canonical changes仍為0。

### 程式修改與原因

新增`decision-02-subaru-brz.json`，保存原始問題、回答、時間、窄化後scope與packet SHA。事件只確認
HYY12的`variant_note = 2nd Color - Zamac`；HYW99、HYY12、JBB55各自的color、wheel type、
tampo、edition和packaging variant均明列unknown，三個兩兩關係均為different release。這讓「來源
真的寫了什麼」與「我們能否知道實體車色」成為兩個可獨立稽核的決定。

原validator的required field集合只涵蓋candidate fields加五種physical fields，無法合法表達來源列上
值得owner單獨確認的variant note。因此加入`additional_required_fields`契約：額外欄位必須存在於同一
packet row，且一旦宣告就進入exact required set，不能多填、漏填或跨row引用。同時把owner response
驗證由硬編碼`繼續下一步`改為要求非空原文，讓每個decision event能保存實際回答；測試仍逐事件核對
預期問答與scope。新增Subaru正常路徑、唯一confirmed note、physical unknown與pair結果測試，並同步
更新spec、roadmap、README、決策記錄、驗收證據與AI rubric。

### 技術選型、替代方案與代價

選擇確認字面`variant_note`，而不是把Zamac寫入`color`或自動合併到舊有Walmart Exclusive variant。
「2nd Color - Zamac」能證明來源如何描述這一列，但沒有足夠row-level authority證明我們資料模型中的
實體色值，也沒有可靠join把它對應到另一份family-level人工標籤。代價是搜尋者暫時只能看見文字note，
不能用結構化color篩選；好處是後續取得圖片或可信release page時，可以新增證據而不用撤回錯誤真值。

validator採通用的額外欄位清單，而不是寫死Subaru/HYY12特例，因為未來其他family也可能出現有價值但
不屬於physical五欄的source observation。這個擴充仍保持fail-closed：欄位必須屬於packet、值必須等於
raw或candidate evidence、決定總集合必須精確相等。相較允許任意JSON欄位，稍微增加event撰寫成本，
但避免理由文字被拿來創造新事實。

### 決策改變與觸發證據

上一輪日誌曾把待確認問題簡化成「能否確認HYY12的Zamac finish」。實際審查後將它再窄化：只確認
來源的完整字串`2nd Color - Zamac`，不宣告Zamac是已驗證的實體color。觸發原因是packet的Subaru
證據只有family-level重疊，沒有row-level join authority；同時三個不同toy numbers及base/2nd/3rd
release markers足以支持owner採用「不同release」的保守分類，但不支持猜測它們各自外觀。

### 驗證證據

Decision event SHA為`119b972f7108222ef50b3ded3d1b38608f679bbbd5f47ef5c2b91eb4954f3cf1`，
綁定packet SHA`2e2adee366d968b0308d64dbde6b513e53055316b5ec5d58c6e0f4b7ae2700b2`。
Validator重算結果為required fields16、confirmed1、unknown15、different-release pairs3、canonical0；
Lamborghini與Subaru兩個events均PASS。

聚焦decision測試13項、完整測試592項全部PASS；Ruff F/I、strict MyPy、compileall和兩個CLI artifact
validation均PASS。完整測試只保留既有Starlette／AnyIO deprecation warning，沒有本次新增失敗。

### 未完成、風險與下一步

VAR-REVIEW1目前完成2/4，仍有Nissan與Audi。Subaru的五種physical fields仍未知、沒有canonical UUID，
本次也沒有重開Fandom網站或取得新的來源授權。下一步應先審Nissan：它有三個不同toy numbers與
base/2nd/3rd markers；HYX54另有明確Tooned tool lineage candidate，但同名casting也出現在非Tooned
工具中。應把release關係、可確認的來源欄位與family/tool歧義分開判斷，不從URL中的`metalflake-blue`
自行填入color。owner確認後才能建立decision03；Audi仍保持pending。
