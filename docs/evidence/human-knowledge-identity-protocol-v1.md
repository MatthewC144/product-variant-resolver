# Identity-Bounded Retrieval — IBR-T1 Protocol Freeze

Date: 2026-09-13 local / approval recorded 2026-09-14T01:29:45Z UTC. Mode: Lite.
Engineering checkpoint: PASS. V4 retrieval, accuracy and latency: NOT EVALUATED.

## Approval and freeze

The owner's `執行下一步` instruction immediately followed the explicit requirements/design/tasks
confirmation handoff. It confirms all three unchanged specifications from commit
`880e4f5b7c556a50e35de900a530e16280bab833` and authorizes IBR-T1. The recorded
[owner approval](../../data/evaluation/human-knowledge-identity-development-v1/owner-approval.json)
binds exact hashes and the historical approved text is copied into `approved-specs/`. Those snapshots
retain their pre-approval proposed headers; approval is a separate attributable event, not a rewrite
of old text. Current live spec status/checkbox updates do not alter frozen approved snapshots.

The [protocol](../../data/evaluation/human-knowledge-identity-development-v1/protocol.json),
SHA-256 `31802be99f02698423c4526bbd8752e6f517fcbef8ca8080926d019f55083fde`, freezes admission
fields/noise policy, character formula, limits, original 21 settings, safety/quality/cost gates,
199 dev-query IDs and 120 scale-query/target pairs. Its manifest binds the builder, normalizer,
frozen corpora/development/governance files, original v3 diagnostic report and every delivered file.
The old final v1 files are not loaded by this builder. No v4 provider/index/ranking is executed.

## Static identity validation

| Measure | Real corpus | Synthetic corpus |
|---|---:|---:|
| Documents | 142 (100 provisional, 42 family) | 3,000 family |
| Deduplicated spaced/compact forms | 284 | 12,000 |
| Maximum forms/document (ceiling 32) | 2 | 4 |
| Unique gram posting keys | 3,052 | 2,332 |
| Form/gram references | 8,051 | 257,640 |
| Maximum query forms in workload (ceiling 256) | 90 | 60 |
| Cross-casting core collisions | 0 | 0 |

All identity forms remain nonempty and long enough for bigrams. Two real collision groups contain
three `83 Chevy Silverado` variants and two `Toyota Supra` variants. These are existing same-casting
variant distinctions, not accidental merging of different casting names; every knowledge ID remains
separate. The [complete core audit](../../data/evaluation/human-knowledge-identity-development-v1/identity-core-audit.json)
shows all forms and groups. Gram references are static construction counts, not a built runtime
weighted index, memory measurement, query visit count or speedup. V3's document postings and these
form postings have different definitions/fields and must not be called a measured cost reduction.

## Workload and limitations

Scale queries: 20 original dev cost queries, 60 exact targets 0000–0059, 20 `Scale` → `Scxle` probes
0060–0079, 20 contextual targets 0080–0099. Original cost queries carry no synthetic correctness
label; positive probe IDs/UUIDs bind the deterministic synthetic documents. Later gates require all
60 exact/all 20 contextual hits and at least 17/20 edited hits, plus p95 ≤150 ms. Real queries
still require unchanged style/safety gates and p95 ≤25 ms. Positive budget abstentions are misses.

An important static limitation is explicit: `scale`, `vehicle`, `model` are removed whole tokens,
so synthetic casting cores are numeric-only; the edited `Scale` wrapper is not a retained-core typo.
These probes prevent an entirely empty fast implementation from passing, but cannot prove true
casting-name typo robustness. Do not replace them after observing output or generalize them to real
coverage. The existing 199 cases are viewed/identity-derived development data, not fresh blind data.
A later independently authored/owner-approved unseen final set remains mandatory.

## Verification

New focused suite: **12 passed**. Full repository: **248 passed**, no skips, one existing Starlette/
AnyIO deprecation warning. Tests verify byte reproduction/portable snapshots, guarded no-v1 reads/
no retrieval calls, approval/disclosure, exact audit/workload/target counts, allowlisted fields,
Unicode/whole-token/numeric policy, empty/short/duplicate/too-many forms, query/window limits, all
file/source bindings, invalid-input preservation and non-overwriting idempotent freeze.

```text
python scripts/build_human_knowledge_identity_protocol.py --freeze
python scripts/build_human_knowledge_identity_protocol.py --check
pytest -o addopts='' -q tests/test_human_knowledge_identity_protocol.py
pytest -o addopts='' -q
ruff check --select F,I scripts/build_human_knowledge_identity_protocol.py tests/test_human_knowledge_identity_protocol.py
MYPYPATH=src mypy --follow-imports=skip scripts/build_human_knowledge_identity_protocol.py
python -m compileall -q scripts tests src
git diff --check
```

Commands ran with local `.venv/bin/` executables and `PYTHONPATH=src` where required. All pass.
Original 199-case builder, v3 JSON/Markdown checks and v1 final report reproducibility also pass;
no historical source/corpus/report changes occurred. The first builder attempt correctly stopped
before output because the Markdown fence language `text` was mistakenly parsed as a noise token;
the parser now strips the language line. Initial isolated type checks required `MYPYPATH=src` and
explicit set annotations. These are pre-output builder corrections, not policy/parameter tuning.

## Handoff

IBR-T1 freezes/commits the protocol before IBR-T2 implementation and any IBR-T3 output. Next: build
the isolated v4 retriever and mathematical-oracle/runtime-isolation tests against this fixed contract.
No latency success, selected v4 artifact, new final queries, canonical change, SQL write or real
3,000-row expansion is authorized by this checkpoint. Default v2/T49 blockade remain unchanged.
