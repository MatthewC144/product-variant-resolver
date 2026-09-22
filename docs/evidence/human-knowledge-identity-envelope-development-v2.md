# Human Knowledge query-global identity-envelope v2 — evidence

Date: 2026-09-22. Lite / Lean Industrial. Verdict: **valid historical experiment; no policy qualified**.

## Purpose and freeze boundary

V2 replaces HIC-v1's candidate-specific query span with one query-global identity envelope. Every
candidate receives the same normalized atoms, offsets, model-number frames, and checksum. The
experiment allows one general leading-year shorthand (`88`/`1988`) while retaining incompatible
model digits such as `R33`/`R34` and `M2`/`M4` as explicit conflict evidence.

Historical calibration deliberately precedes the proposed new 16-positive/16-negative holdout. At
least one non-reference policy had to pass every existing gate before protocol freeze or new
retrieval. None did, so the experiment stopped after rescoring committed public evidence.

## Immutable evidence

| Artifact | SHA-256 |
|---|---|
| Development source | `c91d8e253f1cd19cf59b626e794673defe2e28aea6c993cbce350d1698e83a5e` |
| Historical calibration JSON | `fbdc5171f3b1bfbe3f07b207acb56bd9608e2a3136bdff1acb9175e99f1557ce` |
| Calibration manifest | `03eee815b2cb4110e158f2ff02bf51d8b582282c1f050358c3be117ee238eeb5` |
| Calibration Markdown | `7e0fbd7e1f92cf0d043949e0c0fdee69bd4d53f0a9f40fe1a41d466f6b5039be` |
| Preserved HIC-v1 source | `167c03a5e19fae47eb867b8101c26f1c5bf49ca2c80fb2eb9a4e8bfa0660825f` |

The manifest binds the current source plus committed corpus, 223-row upstream selection,
anchor-confidence v4 pack/report, and HIC-v1 pack/protocol/raw artifacts. It records exact
denominators 223/22/24, zero retrieval calls executed, zero eligible non-reference configurations,
and `protocol_created`, `pack_created`, and `raw_created` all false.

## Historical results

| Policy | Eligible | Existing positives | V4 positives | V4 absent nonempty | HIC positives | HIC absent nonempty |
|---|---:|---:|---:|---:|---:|---:|
| `reference-anchor` | no | 168/168 | 10/10 | 11/12 | 12/12 | 10/12 |
| `envelope-numeric` | no | 160/168 | 9/10 | 7/12 | 11/12 | 7/12 |
| `envelope-bilateral` | no | 146/168 | 9/10 | 1/12 | 10/12 | 1/12 |
| `envelope-safe-form` | no | 114/168 | 9/10 | 1/12 | 8/12 | 1/12 |
| `envelope-decision-list` | no | 108/168 | 7/10 | 1/12 | 8/12 | 1/12 |

All policies have zero retrieval and envelope-computation errors. Structural policies improve
negative rejection, but the recall cost begins before absent-identity output reaches zero. Exact
positive-preservation and safety gates therefore reject every policy.

## Reproducibility and QA

```bash
PYTHONPATH=src .venv/bin/pvr-develop-human-knowledge-identity-envelope --check
```

Two repeated integrity checks return `valid`, `historical_calibration_fail`, and `winner: null`.
The second freeze attempt returns `calibration_failed_unchanged`. Twenty-five focused tests,
77 related tests, and 813 complete repository tests pass; the only suite warning is the existing
Starlette/AnyIO deprecation warning. Targeted Ruff/format, targeted MyPy, compileall, artifact hash
checks, and `git diff --check` pass.

Repository-wide Ruff/MyPy are tracked debt rather than claimed green gates: Ruff identifies 83
legacy files that would be reformatted; MyPy reports 51 existing/cross-module issues. The frozen v2
source is not rewritten after the failed calibration.

## Release boundary

No protocol, new holdout, negative declarations, raw retrieval, selection winner, private
evaluation, API change, Dual RAG integration, PostgreSQL change, canonical identity, release
promotion, variant UUID, color, wheel, tampo, edition, or packaging claim was created. The result is
useful negative evidence, not a deployable admission policy.
