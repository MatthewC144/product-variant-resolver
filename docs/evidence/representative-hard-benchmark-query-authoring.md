# RHB-T5 output-blind query authoring evidence

Date: 2026-10-04
Mode: Lite / Lean Industrial
Verdict: **ENGINEERING PASS — 60-CASE ARTIFACT CREATED; REPRESENTATIVE COVERAGE BLOCKED**

## What was authorized and built

The project owner authorized only RHB-T5 query-pack authoring in a new independent agent. The agent
could read the Git-ignored query-only projection but not the mixed raw source, resolver output,
human labels, failure categories or split. Raw rows had to remain local-only, while Git could retain
only a safe aggregate manifest. RHB-T6 labels, RHB-T7 split and resolver evaluation were explicitly
excluded.

That session created a private 60-case non-synthetic query pack and a public aggregate manifest. The
private pack contains 60 unique query strings, 60 opaque source references and 60 evidence-event
groups across 53 provisional family groups. Every row declares `resolver_output_viewed=false`; the
pack contains no expected status, UUID, correctness, rank or Development/Test assignment and sets
`representative_pilot=false`.

## Code and design decisions

`representative_benchmark_query_authoring.py` implements strict Pydantic contracts for the private
Owner Gate, authoring input, query pack and aggregate manifest. It revalidates the exact T1/T3
permissions and projection hash, binds authoring to the Owner Gate checksum, rejects an authoring
timestamp before authorization, rejects repeated source or evidence events, and atomically installs
private/public outputs. Private paths must be real non-symlink files with `0600` mode inside a real
`0700` directory; the public manifest must be `0644`.

Challenge tags at this phase are deliberately provisional query-surface annotations. QA rejected an
initial attempt to infer catalog-relative meaning from text: `unknown_to_catalog` is prohibited in
RHB-T5, and `same_casting_different_release` requires at least two selected rows in the same
provisional family group. Owner text stays in the ignored authorization ledger; tracked code and the
manifest retain only its SHA-256 binding.

The pre-authoring readiness validator was also made lifecycle-aware. Once the private Owner Gate
exists, it fails immediately with a closed-stage message before loading the mixed raw source. Tests
still reproduce the historical pre-authorization state in isolation, so both transitions remain
executable without treating readiness as reusable authorization.

## Privacy and reproducibility

- Private directory mode: `0700`.
- Projection, authorization, authoring input and query-pack modes: `0600`.
- Public query-pack manifest mode: `0644`.
- Private query-pack SHA-256:
  `97f7f0dd61cf619bb16b198778356d8ef53c7a504086f11542922f90706a858a`.
- Public manifest file SHA-256:
  `8f2927a8f4f318d073793d161c310e319b6ac656c63e2cb20ef60565c1b31949`.
- Projection SHA-256:
  `d5712684cf73c29dd9ea7f385f78c03eb1c8300ce35afd477c0d09ad0d9032dd`.
- Owner authorization ledger SHA-256 binding:
  `75c637354986e8667168276f661ef8c42918a24906e5d698d512192b49631237`.
- Two real `--check` replays returned `unchanged / unchanged`.
- Git positively ignores all three new private RHB-T5 files, and `git ls-files` rejects the private
  query-pack path.

The public manifest contains no query text, source reference, family/evidence key, owner response,
personnel role, label, failure category, split, resolver output or rank. It reports only safe
hashes, counts, negative leakage flags and provisional challenge aggregates.

## Honest data Gate result

The query-surface counts and shortfalls against the minimum of four are:

| Provisional class | Count | Shortfall |
|---|---:|---:|
| Same casting / different release | 9 | 0 |
| Alias or abbreviation | 43 | 0 |
| Missing metadata | 35 | 0 |
| Conflicting year | 1 | 3 |
| Conflicting color | 1 | 3 |
| Conflicting series | 0 | 4 |
| Conflicting identifier | 2 | 2 |
| Distractor quantity or lot | 32 | 0 |
| Unknown to frozen catalog | 0 | 4 |

These counts are not owner-verified failure labels. The last class cannot be established in an
output-blind query-only session. Consequently the artifact is useful provenance and authoring
evidence, but RHB-R10/R11 do not pass and the project must not call it the representative v1 pilot.

## Verification

- `112` representative-benchmark tests passed.
- Ruff and format checks passed for all touched authoring/readiness code and tests.
- Strict MyPy reported no issues in the authoring, readiness and CLI modules.
- Python compile checks passed.
- Deterministic authoring replay returned `unchanged` twice.
- Filesystem permission, Git-ignore, non-tracking, manifest privacy and atomic rollback checks passed.
- `git diff --check` passed.

No RHB-T6 label, RHB-T7 split, resolver, RAG, embedding, Pointwise or Listwise evaluation was run.
