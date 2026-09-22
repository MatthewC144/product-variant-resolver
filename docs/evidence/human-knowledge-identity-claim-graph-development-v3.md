# Human Knowledge identity-claim graph v3 — evidence

Date: 2026-09-22. Lite / Lean Industrial. Verdict: **valid historical experiment; no policy qualified**.

## Purpose and branch boundary

V3 tests whether one candidate-independent identity-claim graph plus an all-rank hard-conflict
preflight can preserve legitimate public query variants while rejecting corpus-absent identities.
It replaces HIE-v2's linear envelope with auditable identity, context, unresolved, and local numeric
frame claims. It does not alter the production retriever.

Historical calibration deliberately runs before a proposed 16-positive/16-negative holdout. A
non-reference policy had to pass every exact 223/22/24 public gate before protocol freeze or new
retrieval. None did, so the experiment stopped on the historical-FAIL branch.

## Immutable evidence

| Artifact | SHA-256 |
|---|---|
| V3 development source | `998f5af0983517d5ead54cf5fddaf46a57056245f92ac6d0c00c3279260ab173` |
| Historical calibration JSON | `d2d94334d311c84e17c98b2f7d38876674ecf9def1c0dda6c889fbc822a7b1c2` |
| Calibration manifest | `9666ff2b5c63677fbc6f74daf9f4490e191c9a209151c798e44e75cccb2cac5f` |
| Calibration Markdown | `16f5b425c6c3e4f7947f868112663a1e024c0270484ebea34fcfe7f583b460a5` |
| Preserved HIC-v1 source | `167c03a5e19fae47eb867b8101c26f1c5bf49ca2c80fb2eb9a4e8bfa0660825f` |
| Preserved HIE-v2 source | `c91d8e253f1cd19cf59b626e794673defe2e28aea6c993cbce350d1698e83a5e` |

The manifest binds the source, corpus, 223-row upstream selection, v4 22-row evidence, HIC-v1
24-row evidence, and the prior HIE-v2 null result. It records zero retrieval calls, zero eligible
non-reference configurations, `private_local_artifacts_read: false`, and
`protocol_authorized: false`.

## Historical results

| Policy | Eligible | Existing positives | V4 positives | V4 absent nonempty | HIC positives | HIC absent nonempty | R32/R33 vetoes | Prior required |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `reference-anchor` | no | 168/168 | 10/10 | 11/12 | 12/12 | 10/12 | 0/2 | 24/24 |
| `claim-conflict-veto` | no | 166/168 | 9/10 | 11/12 | 12/12 | 10/12 | 0/2 | 24/24 |
| `claim-bilateral` | no | 134/168 | 4/10 | 0/12 | 8/12 | 0/12 | 2/2 | 19/24 |
| `claim-query-conservation` | no | 129/168 | 3/10 | 0/12 | 8/12 | 0/12 | 2/2 | 8/24 |
| `claim-decision-list` | no | 131/168 | 4/10 | 0/12 | 8/12 | 0/12 | 2/2 | 3/24 |

All configurations have zero retrieval, graph, alignment, and decision errors. The two looser
policies preserve recall but fail negative safety. The three stricter policies satisfy the measured
negative and BNR34 conflict gates but fail positive preservation. The frozen ordering therefore has
no eligible input to select and returns `winner: null`.

## Reproducibility and QA

```bash
PYTHONPATH=src .venv/bin/pvr-develop-human-knowledge-identity-claim-graph --check
```

Repeated freeze returns `calibration_failed_unchanged`; repeated `--check` recomputes a valid
historical failure. Fifty-one focused tests, 196 related regressions, and all 864 repository tests
pass. Targeted Ruff format/check, target-local strict MyPy with imports skipped, compileall,
installed CLI, SHA-256 checks, artifact shape checks, and `git diff --check` pass. Repository-wide
MyPy still reports 51 known existing/cross-module errors in 18 files and is not represented as
green. The only suite warning is the existing Starlette/AnyIO deprecation warning.

## Release boundary

Exactly three v3 calibration files exist. There is no protocol, holdout declaration, 16+16 pack,
raw retrieval, selection, private evaluation, runtime import, API change, Dual RAG integration,
PostgreSQL change, canonical identity, release promotion, variant UUID, color, wheel, tampo,
edition, or packaging claim. This is reproducible negative evidence, not a deployable policy.
