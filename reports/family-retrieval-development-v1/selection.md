# Human Knowledge v3 — Development Selection

Verdict: FAIL; winner: None

199 identity-derived, intentionally leaky development cases; not final accuracy.
All 21 precommitted configurations were executed. Raw JSON retains every ordered
Top-5 candidate, score, expected identity, latency sample, and source checksum.

| Floor | Char weight | Recall@1 | Recall@5 | MRR@5 | Unrelated nonempty | Merge hits | 142 p50/p95 ms | 3000 p95 ms | Rejection reasons |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0.25 | 0.5 | 0.6905 | 0.9762 | 0.8323 | 10/20 | 4/4 | 8.62/31.34 | 347.29 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.25 | 1.0 | 0.9583 | 1.0000 | 0.9792 | 10/20 | 4/4 | 9.09/32.61 | 355.94 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.25 | 1.5 | 0.9583 | 1.0000 | 0.9792 | 10/20 | 4/4 | 9.57/32.90 | 351.69 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.3 | 0.5 | 0.6905 | 0.9762 | 0.8323 | 10/20 | 4/4 | 8.76/30.20 | 358.90 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.3 | 1.0 | 0.9583 | 1.0000 | 0.9792 | 10/20 | 4/4 | 8.53/29.75 | 346.26 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.3 | 1.5 | 0.9583 | 1.0000 | 0.9792 | 10/20 | 4/4 | 8.84/30.51 | 349.65 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.35 | 0.5 | 0.6905 | 0.9762 | 0.8323 | 10/20 | 4/4 | 8.51/29.60 | 349.81 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.35 | 1.0 | 0.9583 | 1.0000 | 0.9792 | 10/20 | 4/4 | 8.54/30.00 | 338.17 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.35 | 1.5 | 0.9583 | 1.0000 | 0.9792 | 10/20 | 4/4 | 9.41/32.90 | 357.52 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.4 | 0.5 | 0.6905 | 0.9762 | 0.8323 | 10/20 | 4/4 | 9.41/36.60 | 356.47 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.4 | 1.0 | 0.9583 | 1.0000 | 0.9792 | 10/20 | 4/4 | 9.70/34.25 | 377.28 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.4 | 1.5 | 0.9583 | 1.0000 | 0.9792 | 10/20 | 4/4 | 9.13/29.76 | 341.38 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.45 | 0.5 | 0.6905 | 0.9762 | 0.8323 | 10/20 | 4/4 | 8.52/29.62 | 351.75 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.45 | 1.0 | 0.9821 | 1.0000 | 0.9911 | 10/20 | 4/4 | 8.57/29.83 | 343.48 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.45 | 1.5 | 0.9821 | 1.0000 | 0.9911 | 10/20 | 4/4 | 8.52/29.67 | 341.76 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.5 | 0.5 | 0.6905 | 0.9762 | 0.8323 | 10/20 | 4/4 | 8.60/29.54 | 347.45 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.5 | 1.0 | 0.9821 | 1.0000 | 0.9911 | 10/20 | 4/4 | 9.44/31.54 | 337.15 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.5 | 1.5 | 0.9821 | 1.0000 | 0.9911 | 10/20 | 4/4 | 8.56/29.57 | 339.19 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.55 | 0.5 | 0.6905 | 0.9762 | 0.8323 | 10/20 | 4/4 | 8.67/29.37 | 338.47 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.55 | 1.0 | 0.9762 | 0.9940 | 0.9851 | 10/20 | 4/4 | 8.56/29.51 | 340.58 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |
| 0.55 | 1.5 | 0.9762 | 0.9940 | 0.9851 | 10/20 | 4/4 | 8.61/29.68 | 338.56 | unrelated_nonempty, real_142_latency_above_25ms, synthetic_3000_latency_above_150ms |

## Measurement boundary

Runtime: `{'candidate_k': 5, 'clock': 'perf_counter_ns', 'cpu_count': 10, 'machine': 'arm64', 'process_count': 1, 'processor': 'arm', 'python': '3.12.13', 'scale_query_case_ids': ['frd-hold-089ff8645b5f2de7', 'frd-hold-0e07a7139454d2e8', 'frd-hold-369b0be5855c0a1c', 'frd-hold-4f9ee66afdfe8cac', 'frd-hold-8403e21a29c27eab', 'frd-hold-8d24c626a51b1804', 'frd-hold-c639dc688e21d33b', 'frd-merge-04829924a36830a6', 'frd-merge-6062af64f2e5a66c', 'frd-merge-aa499ddb791c6991', 'frd-merge-b60363832032d566', 'frd-positive-0573861db69878eb-abbreviation-numeric', 'frd-positive-0573861db69878eb-contextual-noise', 'frd-positive-0573861db69878eb-single-edit', 'frd-positive-0573861db69878eb-spacing-punctuation', 'frd-positive-08cb7fadb9fed12d-abbreviation-numeric', 'frd-positive-08cb7fadb9fed12d-contextual-noise', 'frd-positive-08cb7fadb9fed12d-single-edit', 'frd-positive-08cb7fadb9fed12d-spacing-punctuation', 'frd-positive-1555c05ceeb491cb-abbreviation-numeric'], 'synthetic_construction': '3000 unique Scale vehicle model NNNN with Synthetic casting aliases', 'system': 'Darwin', 'transport': 'in_process'}`

Each configuration: three warmed queries, all 199 development queries on 142
typed documents, first 20 case-ID-ordered development queries on 3000 synthetic
family documents. Nearest-rank percentiles; K=5; one process; index-build time
excluded. Synthetic common-word identities deliberately stress shared postings.
No PostgreSQL, network, concurrent load, independent final accuracy or production claim.

FAIL preserves v2. No grid expansion, gate relaxation, runtime artifact, new final
holdout or database promotion is authorized by this report.
