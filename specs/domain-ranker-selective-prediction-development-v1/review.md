# Domain ranker and selective prediction development v1 — Lite QA review

Date: 2026-10-09. Reviewed scope: **DRSP-T4 only**. Verdict: **PASS**.

## Coverage

| Requirement | Evidence | Result |
|---|---|---|
| DRSP-R1/R2 | Checksum-bound T4 authorization, permanent holdout/no-match guardrails | PASS |
| DRSP-R7 | Frozen base revision, binary recipe, two seeds, deterministic early stopping | PASS |
| DRSP-R14 | Recursive exact 14-file package allowlist and nested default-deny Git rules | PASS |
| DRSP-R15 | Safetensors-only weights, hashes, code/data lineage, license/NOTICE/model card, offline load | PASS |
| DRSP-R16 | No final evaluation, runtime activation, endpoint or FastAPI default change | PASS |

The focused T1–T4 and FastAPI regression suites pass. Ruff, strict MyPy, `git diff --check` and
`python -m product_variant_resolver.domain_ranker_training --check` pass. Both checkpoint files load
offline with `trust_remote_code=false`; each is below 50 MiB. Unexpected nested files and optimizer
state are rejected by both the package validator and Git ignore contract. Two consecutive clean
rebuilds produced identical checkpoint and package SHA-256 values; public text assets contain no
CRLF whitespace findings.

## Findings and corrections

1. The first launch failed before training because AdamW requires `lr`, not `learning_rate`.
2. The first completed training attempt was not released because the safetensors validator used an
   incompatible iteration assumption. Scratch weights were deleted, the validator received a real
   safetensors regression test, and training was rerun from the pinned base model.
3. The legacy governance test expected one root checkpoint; it now validates the two exact seed
   paths and confirms every unexpected checkpoint/optimizer path stays ignored.
4. A Git whitespace check exposed CRLF tokenizer metadata, and a subsequent rebuild exposed
   nonessential safetensors-header byte variance. Text output is now LF-normalized; tensor metadata
   lives only in the canonical manifest, making the final package byte-reproducible.

No High/Critical finding remains in the T4 scope. The existing Starlette/AnyIO deprecation warning
is third-party and unrelated to the checkpoint path.

## Carry-forward

T4 selection MRR is early-stopping evidence, not proof of value over the generic ranker. DRSP-T5
must use the identical T2 pools, compare generic plus both seeds, enforce the frozen ranker and
latency gates, and return `winner: null` on failure. T5, calibration, final evaluation and runtime
activation remain unauthorized.
