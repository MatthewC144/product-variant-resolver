# AI eval — Neural reranker architecture comparison v1

Date: 2026-09-25. Scope: 100-case synthetic/curated fixture benchmark. Verdict:
**PASS for experiment integrity; FAIL for neural promotion**.

| Rubric area | Result | Evidence and boundary |
|---|---|---|
| Grounding | PASS | Every ranked identity comes from the frozen 120-product canonical fixture catalog; neither neural arm can synthesize a candidate. |
| Candidate parity | PASS | Each of 21 Test rows has one shared 25-UUID candidate set; all three arms consume exactly that set. |
| Label leakage | PASS | Formal raw collection is recursive-label-blind; fitting reads Train/Dev only and Test labels join only after raw hash freeze. |
| Pointwise independence | PASS | MiniLM receives independent query/candidate pairs; real reversed-batch scores map within `1e-6`. |
| Listwise authenticity | PASS | The attention head receives the whole candidate feature set; real permutation and padding preflights pass. |
| Feature safety | PASS | Predictive inputs are allowlisted text/signals/retrieval evidence; case/split/expected/private/Human Knowledge outcomes are excluded. |
| Model provenance | PASS | Model ID, immutable revision, Apache-2.0 license, six-file allowlist, safetensors hashes, CPU float32 and 33 dependency pins are recorded. |
| Training isolation | PASS | 36 matched Train lists fit weights/normalizer; 12 matched Dev lists only select earliest epoch 1; Test does not select the model. |
| Evidence integrity | PASS | Protocol, pool, model, raw, report, Markdown and SVGs are checksum-bound; repeat phases are `unchanged` and tampering fails closed. |
| Ranking quality | TIED | RRF, pointwise and listwise each achieve Top-1/MRR/Recall `12/12` and hard-negative `4/4`; every paired target rank is unchanged. |
| Value gate | FAIL | Both neural arms have Top-1 gain `0.00`, below the predeclared `0.05` requirement. |
| Latency/error safety | PASS | Neural resolver p95 is below 90 ms versus the 1,500 ms budget; collection errors are zero. |
| Selection integrity | PASS | Neither neural arm passes all gates, so the deterministic result is `winner: null`; no closest-model promotion or Test retuning occurs. |
| Explainability | PASS | Report exposes candidates, source/RRF ranks, neural scores/ranks, structured evidence, timings, paired transitions, categories and model versions. |
| Claim calibration | PASS | README/report name exact 12-case denominator, fixture dataset, hardware and limitations; raw scores are explicitly not probabilities. |
| Release safety | PASS | Runtime remains RRF; API, calibration, Dual RAG, PostgreSQL, canonical data and Human Knowledge/release state are unchanged. |

The evaluated AI behavior is ranking, not generated prose. Green software tests prove deterministic
implementation and evidence integrity; the ranking-quality tie does not establish general model
quality. The fixture baseline is already at the ceiling, so the only defensible conclusion is that
neither neural architecture demonstrated incremental value on this versioned Test.

The most important positive result is methodological: one-time label-blind collection, genuine
pointwise/listwise separation, immutable local-model provenance, paired evidence and an enforced null
branch prevent a visually impressive neural component from being promoted without measured value.
