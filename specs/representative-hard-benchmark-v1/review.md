# Representative Hard Benchmark v1 — Lean QA Review

Date: 2026-09-26. Mode: Lite / Lean Industrial. Scope: **RHB-T1 recheck 2 only**.

## Verdict: PASS

RHB-T1 now produces a truthful, deterministic and clean-checkout-portable source baseline. The two
earlier blockers are resolved:

1. all six entries separate current repository/publication reality from known rights evidence and
   prospective RHB-v1 use/redistribution; and
2. the 1,763-row owner aggregate is now read only from the Git-tracked
   `reports/local-release-staging-v1/manifest.json`, while the ignored local review summary is not a
   required input and is not listed in the repository tracking contract.

The inventory still authorizes no new source use. Human-label rows and their alignment are recorded
as already public/Git-tracked, but future benchmark use and republication remain blocked pending
RHB-T3. Owner workbook rows remain private and untracked; only aggregate counts and non-reversible
checksums are public.

## Checked items

- All six source entries' current repository/publication state, known rights evidence, prospective
  benchmark use, prospective redistribution, owner decision and authority boundary.
- Human labels/alignment: current row-level publication is explicit; future use/republication is
  blocked pending RHB-T3; existing publication is not treated as new permission.
- Owner snapshot: 1,763 private observations remain untracked; the tracked public manifest contains
  only counts/checksums; the ignored review summary is absent from required inputs and contracts.
- Wiki pilot: 100 attributed public text rows remain staging-only, without canonical UUIDs or new
  collection authority.
- Counts/checksums, `0 exact / 2 family-only / 99 unmapped`, zero owner promotions/links, zero
  network requests and zero copied private owner rows.
- Every path in `repository_tracking_contract.artifacts` is verified with
  `git ls-files --error-unmatch`.
- A fresh-clone-shaped temporary tree containing only public inputs can build the baseline.
- Repeated deterministic checks, focused tests, Ruff, format, strict MyPy, compileall and
  `git diff --check`.
- Allowed scope: no product/runtime/API/model/database source file changed.

## Requirement coverage

| Requirement | Evidence | Result |
|---|---|---|
| RHB-R1 | Six entries record origin, acquisition, count, checksum, current publication/repository state, known rights, prospective use/redistribution and unresolved owner decisions. Public human artifacts, private owner rows/public aggregate, and attributed Wiki derivatives are represented accurately. | PASS |
| RHB-R7 | Human Knowledge/family alignment, owner staging and Wiki staging remain non-canonical. Alignment is `0 exact / 2 family-only / 99 unmapped`; owner promotions/links are zero; Wiki canonical UUIDs are null. | PASS |
| RHB-R19 | Stable JSON, schema/version metadata, generator/input/inventory hashes, exact counts/order, atomic output, drift rejection, repeated `unchanged`, Git tracking validation and fresh-clone-shaped public-input construction all pass. | PASS |

## Findings

### Blocker

- None.

### Important

- None for RHB-T1.

### Later

- RHB-T3 must still obtain explicit owner decisions for every future source/use/publication pair.
  This T1 PASS records present facts only and does not authorize benchmark reuse, republication,
  collection, labeling or canonical promotion.
- Exact real-variant authority remains absent. RHB-T4 must independently prove any matched UUID;
  neither family context nor staged release rows can supply it.

## Reproduction and evidence

```text
.venv/bin/python scripts/build_representative_hard_benchmark_source_inventory.py --check
unchanged

.venv/bin/python scripts/build_representative_hard_benchmark_source_inventory.py --check
unchanged

PYTHONPATH=src .venv/bin/pytest -o addopts='' -q \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py
7 passed in 0.17s

.venv/bin/ruff check --select F,I \
  scripts/build_representative_hard_benchmark_source_inventory.py \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py
All checks passed!

.venv/bin/ruff format --check \
  scripts/build_representative_hard_benchmark_source_inventory.py \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py
2 files already formatted

.venv/bin/mypy --strict --follow-imports=skip \
  scripts/build_representative_hard_benchmark_source_inventory.py \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py
Success: no issues found in 2 source files

.venv/bin/python -m compileall -q \
  scripts/build_representative_hard_benchmark_source_inventory.py \
  tests/evaluation/test_representative_hard_benchmark_source_inventory.py src
PASS

git diff --check
PASS
```

Independent tracking verification:

```text
TRACKED data/benchmark.json
TRACKED data/catalog.json
TRACKED data/human_labeled_names.json
TRACKED data/human_labeled_catalog_alignment.json
TRACKED reports/local-release-staging-v1/manifest.json
TRACKED data/external/hot-wheels-wiki/pilot-2025/manifest.json
TRACKED data/external/hot-wheels-wiki/pilot-2025/normalized.json
TRACKED data/external/hot-wheels-wiki/pilot-2025/raw.json
```

The ignored path
`data/external/hot-wheels-wiki/local-release-casting-review-v1/manifest.json` is verified as
untracked/ignored and appears in neither `input_artifacts` nor
`repository_tracking_contract.artifacts`.

## Recommended next task

Proceed to RHB-T2: implement the strict benchmark contracts and fail-closed validators. Preserve the
T1 source/publication boundaries and do not advance to case authoring until the later owner source
and catalog-authority Gates pass.
