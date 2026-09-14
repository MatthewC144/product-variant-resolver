# Final-v2 family retrieval and Lite/runtime closure

Date:2026-09-14. IBR-T5 family-quality/engineering/runtime PASS. T49 DESIGN ONLY permitted.
No canonical/release-variant/production-accuracy or deployment/ingestion approval.

## Provenance and the only final execution

Qualified winnera9a3730 precedes question8f28918 and owner-approved labels87bbd19. New evaluator
and fake-output tests were frozen atb86578c before final output. Separate integrity preflight
validates committed benchmark/source bytes; the collector does not open approved labels and only
query signals enter retrieval. Zero warmups, exactly105 real final calls. Exclusive run reservation
persists on interruptions; raw rows are durably published before the runner parses labels/scoring.
No alternate floor, rerun, query rewriting, threshold relaxation or dropped denominators.

| Artifact | SHA-256 |
|---|---|
| run-start.json | 2f9601cfb9673be0aeb2dacccff82471fdcbcd56b41ab71826facb19238e987e |
| raw-results.json | 61264a33bdb98e609c868cae59fbba8d067e13d47ff965919bd6a9adb4da4f32 |
| evaluation.json | b59492bb745411a1ab0cbe34b025a99bb3dfcfac86621e5a37f5b6c732a5b8d6 |
| runtime-validation/human-knowledge-v4-ibr-t5.json | 3c4e951978b0aac7947e533180cfb8e884e4bfa6bb5ad4a2d714d9078e156658 |

Final source/benchmark/question hashes and timestamps are in JSON, not inferred from rounded scores.
Pure `--check` reconstructs105 rows, catalog IDs/UUIDs, source scores/ranks/RRF, work/budgets,
event ordering, source/commit provenance, metrics/gates and Markdown without query execution.

## All unchanged final gates

| Gate | Raw result | Threshold | Verdict |
|---|---:|---:|---|
| Positive Recall@5 | 80/84=.952381 | ≥.85 | PASS |
| Positive Recall@1 | 77/84=.916667 | ≥.65 | PASS |
| MRR@5 | (78.33333333333333)/84=.932540 | ≥.75 | PASS |
| Marketplace Recall@5 | 42/42=1 | ≥.75 | PASS |
| Lexical Recall@5 | 38/42=.904762 | ≥.75 | PASS |
| Family coverage@5 | 42/42=1 | ≥.90 | PASS |
| Merge Recall@5 | 4/4=1 | =1 | PASS |
| Forbidden family candidates | 0 | =0 | PASS |
| Unrelated nonempty | 0/10 | =0 | PASS |

Held7 identities remain unmaterialized; other valid hits are permitted. Retrieval errors0; budget/
noise abstentions0. Four missed lexical case IDs18e55e067083dbd1,1b2a4227b4e5decd,4d2de6db3d5bba63,
aab5350cb90d72ed remain in JSON/Markdown, all returned empty. Every positive miss remains over84,
and a family is covered when either of its paired queries hits; denominator42, not84 or all105.

This is output-blind authoring followed by owner review of synthetic same-family target pairs,
not independent-author/live-marketplace/population/unseen-casting truth. Prior development rules
and results were known. Owner approval does not remove construction bias or validate real variants.
Four difficult lexical forms are retained rather than patched against viewed final queries.

## Cost and real packaging verification

Final diagnostic samples105,zero warmups,nearest-rank p50=2.591583ms/p95=6.945209ms on
Python3.12.13/Darwin/arm64,one non-isolated process. Extraction excluded, retrieval and serialization
included. No final latency acceptance threshold was invented. Source-valid T3 real142/synthetic3000
p95=2.065375/45.138542ms and all scale60/20/20 known-target hits remain PASS on frozen workload,
not remeasured here. They exclude HTTP/SQL/network/load and are not production latency.

Fresh dedicated image `product-variant-resolver:ibr-t5-rootfix`, imageID
`sha256:7dbae114eb0615fb8582cce3fc79b2f19233edc453672bc5726de937dfec0fee`, runs Linuxaarch64/
Python3.12.14/uid100,read-only with private tmpfs. Real loopback Uvicorn one-worker HTTP checks
defaultv2 and opt-inv4 health/resolve/UI200, identical non-debug canonical outputs on four existing
fixture queries, typed debug/artifact/work/index evidence, missing/malformed/stale health/resolve503.
No host port is published. All temporary servers terminate; container is removed after the smoke.
The verifier is mounted read-only, not shipped as a production service dependency.

Two failures are preserved under `reports/runtime-validation/*failed-01.json` and `*failed-02.json`.
First, installed-package-derived ROOT sought evidence under/usr/local/lib/python3.12 while data/src
live under/app; v4 correctly failed503. Docker `PYTHONPATH=/app/src` fixes packaging without modifying
source-bound loader/retriever/artifact/bench bytes. Second, a verifier fixture wrongly expected moving
unchanged artifact bytes to make evidence stale; fixed-root evidence legitimately still validates.
The fixture now corrupts mandatory selection evidenceSHA, and the original503 requirement passes.
No model gate was relaxed; no final retrieval was repeated during runtime repair. Old images/failure
records remain available. Runtime report binds verifier, Docker/Compose and all runtime source bytes.

## Actual regression and next authority

32 new evaluator/closure tests PASS;411 full tests PASS,no skips,one existing Starlette/AnyIO warning.
Earlier fake-output tests caught dict-order Markdown reproduction, fixed with sorted JSON before
real execution; a missing private preflight fixture source caused406pass/1fail in the first full
run, corrected before the passing407 pre-final regression and evaluator commit. Focused RuffF/I,
isolated strict MyPy evaluator, compilation, Node UI syntax and static default/postgres Compose PASS.
Original-v1 benchmark/JSON/Markdown,199dev,v3FAIL JSON/Markdown,identity protocol and v4PASS
JSON/Markdown checks remain reproducible. Full-suite tests use fake final retrieval or stored ranks,
not a second real final run. Full-repo historical lint/type debt is not claimed resolved.

AI artifact rubric and QA requirement map are current; narrative log explains outcome/code/method/
trade-offs/decisions/verification. With scoped final, source-valid cost, regressions and runtime all
PASS, T49 design may proceed. No actual PostgreSQL promotion/3,000 real rows/defaultv4 deployment
was run or authorized. Next design must address reviewed release-variant fields and same-casting
color/year/wheel/tampo distinctions before claiming the user's complete variant-resolution goal.
