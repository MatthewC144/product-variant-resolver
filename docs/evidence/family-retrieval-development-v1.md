# Family Retrieval Development v1 — Freeze Evidence

> Date: 2026-09-12
>
> Mode: Lite / Lean Industrial
>
> Status: HRR-T1 PASS; frozen before any v3 retriever/configuration output

## Outcome and boundary

HRR-T1 created a deterministic 199-case `dev` pack for implementing and selecting the proposed
Human Knowledge retriever v3. It contains 168 positive cases—four transformations for each of the
42 accepted review families—plus all 4 merge controls, all 7 hold controls, and 20 unrelated
controls. The unrelated group is split into 10 opaque zero-token-overlap strings and 10 generic
marketplace descriptions with no resolvable catalog identity.

This is intentionally leaky development data. Positive questions are mechanically derived from
the indexed casting identities, and merge/hold questions are derived from review-governance
identities. It may help implement the retriever and select one of the precommitted configurations;
it may not support final accuracy, canonical resolution, calibration, PostgreSQL ingestion, or a
production claim. Both the pack and manifest record `retrieval_executed=false` and
`configuration_output_viewed=false`. No v3 implementation, candidate report, winner, or runtime
artifact was produced in this task.

## What changed and why

`scripts/build_family_retrieval_development.py` is the single authoring and validation path. It
loads the frozen 42-family projection, 42/4/7 review registry, 97-casting human catalog, and their
manifests. The historical v1 query pack is loaded only to reject exact or normalized-equivalent
query reuse; its expected labels, ranks, metrics, failures, and thresholds do not enter generation
or selection.

Each accepted family receives these four deterministic challenge styles:

| Style | Transformation | Problem represented |
|---|---|---|
| `single_edit` | deletes one character in an identity token | ordinary misspelling |
| `spacing_punctuation` | joins multi-token names or splits one-token names | tokenization disruption |
| `abbreviation_numeric` | shortens a word/year or perturbs a model token | abbreviated/numeric listing text |
| `contextual_noise` | wraps the exact identity in marketplace context | relevant identity amid seller noise |

The transformations are algorithms rather than 168 hand-entered strings so a reviewer can
reproduce exactly how every case was made. This also prevents a later implementation from quietly
editing difficult questions after seeing output. The limitation is equally important: generated
examples cannot represent real marketplace frequency or linguistic diversity, so a separate unseen
holdout is still mandatory.

`data/evaluation/family-retrieval-development-v1/development-pack.json` stores the cases, derived
labels, allowed/prohibited uses, and the finite 21-configuration selection contract. The contract
freezes seven character floors (`0.25`–`0.55`) crossed with three character RRF weights (`0.5`,
`1.0`, `1.5`); sparse/dense weights, 192 dense dimensions, RRF `k=60`, and candidate limit 5 remain
fixed. Safety and minimum-quality gates plus the MRR/Recall/floor/weight tie-break are written
before any candidate output exists.

`development-pack-manifest.json` binds the exact development bytes, authoring script, input data,
input manifests, counts, split, leakage disclosure, and zero-output state by SHA-256. The builder
writes only after every source and generated case passes validation and uses an atomic replace for
each final file. Thus malformed input fails before it can overwrite a previously frozen pack.

## Frozen accounting

| Measure | Frozen value |
|---|---:|
| Total dev cases | 199 |
| Positive family cases | 168 |
| Accepted family groups | 42 |
| Positive styles per family | 4 |
| Merge controls | 4 |
| Hold controls | 7 |
| Opaque unrelated controls | 10 |
| Generic unrelated controls | 10 |
| Precommitted configurations | 21 |

The development pack SHA-256 is
`23589b23567220dbba0de959ec5223cf60365b1222320f3a372f1b156244dbe9`. The authoring/validation
script SHA-256 recorded inside the manifest is
`3da7becca7b0cb27568e887140d6f07a1e41c0ceb56d0badce38134bca1a776c`.

## Verification

The following Lite checks passed:

```text
python scripts/build_family_retrieval_development.py --freeze
  froze family-retrieval-development-v1: 199 dev cases; retrieval_executed=false

python scripts/build_family_retrieval_development.py --check
  verified family-retrieval-development-v1: 199 dev cases; retrieval_executed=false

python -m pytest tests/test_family_retrieval_development.py -q
  10 passed

ruff check scripts/build_family_retrieval_development.py \
  tests/test_family_retrieval_development.py
  All checks passed!

mypy scripts/build_family_retrieval_development.py
  Success: no issues found in 1 source file

PYTHONPATH=src python -m pytest -q
  211 tests passed; 1 known Starlette/AnyIO deprecation warning
```

The tests lock exact counts/style coverage, all 42×4 positive combinations, normalized query
uniqueness, v1 non-reuse, opaque zero overlap, generic no-identity behavior, exact 21-config grid,
source/script/output checksums, deterministic byte reproduction, non-mutating `--check`, and
invalid-input preservation.

## Remaining risk and next step

This PASS proves dataset governance and reproducibility, not retrieval quality. The generated data
may be easier or less realistic than live listings, and no configuration is yet known to meet the
safety/quality gates. T49 and PostgreSQL expansion remain blocked.

The next task is HRR-T2: implement the experimental, debug-only character n-gram candidate channel,
typed character evidence, and failure/version metadata while preserving canonical Dual RAG
authority. HRR-T2 must not select or publish a winning configuration; selection belongs to HRR-T3
using only this frozen development pack.
