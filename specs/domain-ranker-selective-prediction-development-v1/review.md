# Domain ranker and selective prediction development v1 — Lite QA review

Date: 2026-10-09. Reviewed scope: **DRSP-T5**. Verdict: **PASS for faithful comparison;
ranker qualification FAIL with `winner: null`**.

## Coverage

| Requirement | Evidence | Result |
|---|---|---|
| DRSP-R1/R2 | Checksum-bound T5 authorization; 53/20 holdouts and 52 no-match rows at zero reads/scores | PASS |
| DRSP-R8 | Identical 30×25 pools; exact/casting Top-1, MRR@10, Recall@25, same-family accuracy and CPU latency | PASS |
| DRSP-R9 | No selected checkpoint after gate failure; T6 stops | PASS |
| DRSP-R14 | Public output contains aggregates only; row diagnostics are ignored and mode `0600` | PASS |
| DRSP-R16 | No calibration, final evaluation, runtime activation or FastAPI default change | PASS |

The evaluator reloaded the frozen generic weights and both T4 safetensors packages offline with
`trust_remote_code=false`. The re-scored generic order matched the T2 frozen order exactly. Every arm
used the same 30 selection queries, 25 candidates, tokenizer, maximum length and one-thread CPU
procedure. Unit tests cover tie order, strict hard-negative comparisons, percentile calculation,
all-or-nothing gates and deterministic winner ordering.

## Result and gate audit

| Metric | Generic | Seed 17 | Seed 29 | Required domain delta |
|---|---:|---:|---:|---:|
| Exact Top-1 | `24/30` | `23/30` | `23/30` | at least `+3` cases |
| Casting Top-1 | `30/30` | `30/30` | `30/30` | at least `-1` case |
| MRR@10 | `0.87777778` | `0.86111111` | `0.86111111` | at least `+0.02` |
| Recall@25 | `30/30` | `30/30` | `30/30` | no regression |
| Same-family accuracy | `41/52` | `40/52` | `40/52` | at least `+0.10` |
| CPU p95 | `243.924917 ms` | `243.6395 ms` | `244.865875 ms` | ≤`1.25×` and ≤`200 ms` |

Both seeds pass casting preservation, Recall@25 and relative latency. Both fail exact Top-1, MRR,
same-family improvement, absolute latency and two-seed positive-direction gates. Because every gate
is mandatory, `winner: null` is correct. The model-training pipeline is valid, but this fine-tuning
recipe did not add measured ranking value.

## Validation and boundaries

Focused comparison/training tests, Ruff, strict MyPy, artifact check mode, the 22-test canonical
FastAPI regression suite and `git diff --check` pass. Public result content SHA-256 is
`d9665b151c4c3263afd8e24345024985904f1a407d93ce6c9173ed37d8444e2b`; its file SHA-256 is
`219789db3f1e6f7e3e114656d165ca3ebe733225139e294787dc64beaa3e25c3`. Private diagnostics file
SHA-256 is `12a2892137cffc9ef08e9fbfe49fcba351ae14b3c1bf0b95fa5491caa3675845` and remains Git-ignored
with mode `0600`.

No High/Critical issue remains in the T5 implementation scope. Calibration cannot begin because R9
requires an immutable selected-ranker checkpoint hash and T5 selected none. A future retry must be a
new versioned experiment with new data/model hypotheses and a new Owner Gate; thresholds or metrics
must not be revised after this result.

The broader `tests/api` run also surfaced 13 pre-existing failures in the separately gated Human
Knowledge storage app: its v4 protocol rejects a stale hash for `retrieval.py`, leaving that
experimental service unavailable with the intended fail-closed 503. T5 did not modify that module,
profile or runtime path. This is recorded rather than silently counted as a T5 regression or repaired
outside scope.
