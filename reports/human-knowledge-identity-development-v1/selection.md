# Human Knowledge v4 — Identity-Bounded Development Selection

Verdict: PASS; winner: {'character_rrf_weight': 1.0, 'character_score_floor': 0.5}

All 21 frozen configurations; 199 already-viewed identity-derived dev cases per setting.
4,179 real outputs plus 2,520 synthetic outputs retain candidates, work and raw latency.
This is development evidence, not final accuracy or real 3,000-row catalog ingestion.

| Floor | Char weight | Positive R@1 | Positive R@5 | MRR@5 | Unrelated nonempty | Merge | Forbidden | Real p50/p95 ms | Scale p95 ms | Exact/edit/context hits | Rejections |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0.25 | 0.5 | 0.9762 | 168/168 | 0.9881 | 0/20 | 4/4 | 0 | 0.23/2.13 | 50.34 | 60/60; 20/20; 20/20 | none |
| 0.25 | 1.0 | 0.9821 | 168/168 | 0.9911 | 0/20 | 4/4 | 0 | 0.32/3.00 | 62.17 | 60/60; 20/20; 20/20 | none |
| 0.25 | 1.5 | 0.9821 | 168/168 | 0.9911 | 0/20 | 4/4 | 0 | 0.23/2.16 | 54.13 | 60/60; 20/20; 20/20 | none |
| 0.3 | 0.5 | 0.9762 | 168/168 | 0.9881 | 0/20 | 4/4 | 0 | 0.22/2.04 | 44.49 | 60/60; 20/20; 20/20 | none |
| 0.3 | 1.0 | 0.9821 | 168/168 | 0.9911 | 0/20 | 4/4 | 0 | 0.23/2.08 | 45.03 | 60/60; 20/20; 20/20 | none |
| 0.3 | 1.5 | 0.9821 | 168/168 | 0.9911 | 0/20 | 4/4 | 0 | 0.22/2.08 | 44.64 | 60/60; 20/20; 20/20 | none |
| 0.35 | 0.5 | 0.9762 | 168/168 | 0.9881 | 0/20 | 4/4 | 0 | 0.22/2.03 | 44.77 | 60/60; 20/20; 20/20 | none |
| 0.35 | 1.0 | 0.9821 | 168/168 | 0.9911 | 0/20 | 4/4 | 0 | 0.23/2.08 | 44.12 | 60/60; 20/20; 20/20 | none |
| 0.35 | 1.5 | 0.9821 | 168/168 | 0.9911 | 0/20 | 4/4 | 0 | 0.22/2.07 | 44.99 | 60/60; 20/20; 20/20 | none |
| 0.4 | 0.5 | 0.9762 | 168/168 | 0.9881 | 0/20 | 4/4 | 0 | 0.22/2.08 | 48.38 | 60/60; 20/20; 20/20 | none |
| 0.4 | 1.0 | 0.9821 | 168/168 | 0.9911 | 0/20 | 4/4 | 0 | 0.21/2.05 | 45.63 | 60/60; 20/20; 20/20 | none |
| 0.4 | 1.5 | 0.9821 | 168/168 | 0.9911 | 0/20 | 4/4 | 0 | 0.22/2.08 | 45.47 | 60/60; 20/20; 20/20 | none |
| 0.45 | 0.5 | 0.9762 | 168/168 | 0.9881 | 0/20 | 4/4 | 0 | 0.21/2.03 | 46.66 | 60/60; 20/20; 20/20 | none |
| 0.45 | 1.0 | 0.9821 | 168/168 | 0.9911 | 0/20 | 4/4 | 0 | 0.21/2.02 | 45.32 | 60/60; 20/20; 20/20 | none |
| 0.45 | 1.5 | 0.9821 | 168/168 | 0.9911 | 0/20 | 4/4 | 0 | 0.21/2.06 | 44.94 | 60/60; 20/20; 20/20 | none |
| 0.5 | 0.5 | 0.9762 | 168/168 | 0.9881 | 0/20 | 4/4 | 0 | 0.21/2.06 | 45.04 | 60/60; 20/20; 20/20 | none |
| 0.5 | 1.0 | 0.9821 | 168/168 | 0.9911 | 0/20 | 4/4 | 0 | 0.21/2.07 | 45.14 | 60/60; 20/20; 20/20 | none |
| 0.5 | 1.5 | 0.9821 | 168/168 | 0.9911 | 0/20 | 4/4 | 0 | 0.21/2.07 | 45.08 | 60/60; 20/20; 20/20 | none |
| 0.55 | 0.5 | 0.9643 | 166/168 | 0.9762 | 0/20 | 4/4 | 0 | 0.22/2.05 | 45.13 | 60/60; 20/20; 20/20 | none |
| 0.55 | 1.0 | 0.9702 | 166/168 | 0.9792 | 0/20 | 4/4 | 0 | 0.22/2.08 | 45.32 | 60/60; 20/20; 20/20 | none |
| 0.55 | 1.5 | 0.9702 | 166/168 | 0.9792 | 0/20 | 4/4 | 0 | 0.21/2.07 | 45.71 | 60/60; 20/20; 20/20 | none |

## Positive styles, work and subgroup cost

| Floor / weight | Edit | Spacing | Abbreviation | Context | Scale original-20/exact/edit/context p95 ms | Real/scale max visits | Real/scale abstentions |
|---|---:|---:|---:|---:|---|---|---|
| 0.25 / 0.5 | 42/42 | 42/42 | 42/42 | 42/42 | 67.86/0.91/1.57/15.32 | 18707/434052 | {'noise_only': 10}/{} |
| 0.25 / 1.0 | 42/42 | 42/42 | 42/42 | 42/42 | 118.85/1.21/2.10/16.64 | 18707/434052 | {'noise_only': 10}/{} |
| 0.25 / 1.5 | 42/42 | 42/42 | 42/42 | 42/42 | 66.81/1.15/1.90/19.54 | 18707/434052 | {'noise_only': 10}/{} |
| 0.3 / 0.5 | 42/42 | 42/42 | 42/42 | 42/42 | 63.65/0.87/1.49/15.34 | 18707/434052 | {'noise_only': 10}/{} |
| 0.3 / 1.0 | 42/42 | 42/42 | 42/42 | 42/42 | 63.69/0.86/1.48/12.12 | 18707/434052 | {'noise_only': 10}/{} |
| 0.3 / 1.5 | 42/42 | 42/42 | 42/42 | 42/42 | 61.19/0.87/1.49/12.02 | 18707/434052 | {'noise_only': 10}/{} |
| 0.35 / 0.5 | 42/42 | 42/42 | 42/42 | 42/42 | 58.93/0.86/1.58/13.26 | 18707/434052 | {'noise_only': 10}/{} |
| 0.35 / 1.0 | 42/42 | 42/42 | 42/42 | 42/42 | 60.13/0.88/1.56/13.47 | 18707/434052 | {'noise_only': 10}/{} |
| 0.35 / 1.5 | 42/42 | 42/42 | 42/42 | 42/42 | 58.95/0.88/1.52/12.62 | 18707/434052 | {'noise_only': 10}/{} |
| 0.4 / 0.5 | 42/42 | 42/42 | 42/42 | 42/42 | 61.68/0.90/1.53/13.80 | 18707/434052 | {'noise_only': 10}/{} |
| 0.4 / 1.0 | 42/42 | 42/42 | 42/42 | 42/42 | 61.47/0.86/1.51/13.61 | 18707/434052 | {'noise_only': 10}/{} |
| 0.4 / 1.5 | 42/42 | 42/42 | 42/42 | 42/42 | 60.84/0.87/1.48/12.50 | 18707/434052 | {'noise_only': 10}/{} |
| 0.45 / 0.5 | 42/42 | 42/42 | 42/42 | 42/42 | 59.36/0.90/1.54/13.14 | 18707/434052 | {'noise_only': 10}/{} |
| 0.45 / 1.0 | 42/42 | 42/42 | 42/42 | 42/42 | 59.68/1.02/1.58/17.42 | 18707/434052 | {'noise_only': 10}/{} |
| 0.45 / 1.5 | 42/42 | 42/42 | 42/42 | 42/42 | 59.23/0.89/1.52/12.46 | 18707/434052 | {'noise_only': 10}/{} |
| 0.5 / 0.5 | 42/42 | 42/42 | 42/42 | 42/42 | 59.27/0.88/1.53/14.47 | 18707/434052 | {'noise_only': 10}/{} |
| 0.5 / 1.0 | 42/42 | 42/42 | 42/42 | 42/42 | 61.22/0.87/1.49/12.24 | 18707/434052 | {'noise_only': 10}/{} |
| 0.5 / 1.5 | 42/42 | 42/42 | 42/42 | 42/42 | 61.37/0.88/1.49/12.77 | 18707/434052 | {'noise_only': 10}/{} |
| 0.55 / 0.5 | 41/42 | 42/42 | 41/42 | 42/42 | 59.59/0.87/1.47/12.79 | 18707/434052 | {'noise_only': 10}/{} |
| 0.55 / 1.0 | 41/42 | 42/42 | 41/42 | 42/42 | 61.08/0.85/1.43/12.79 | 18707/434052 | {'noise_only': 10}/{} |
| 0.55 / 1.5 | 41/42 | 42/42 | 41/42 | 42/42 | 61.40/0.85/1.45/13.74 | 18707/434052 | {'noise_only': 10}/{} |

## Measurement and interpretation

```json
{
  "candidate_k": 5,
  "clock": "perf_counter_ns",
  "cpu_count": 10,
  "host_isolated": false,
  "machine": "arm64",
  "measured_boundary": "retrieve_with_work_only",
  "percentile_method": "nearest_rank",
  "process_count": 1,
  "processor": "arm",
  "python": "3.12.13",
  "system": "Darwin",
  "system_release": "24.6.0",
  "transport": "in_process",
  "warmup_count_per_corpus": 3
}
```

Three warm-ups per corpus/configuration; K=5; nearest-rank percentiles. All 199 real and
120 scale raw samples determine cost gates. Original-20, 60 exact, 20 edited and 20 contextual
scale groups are additionally shown separately; subgroup figures do not replace aggregate gates.
Complete retrieve_with_work timing only: index/startup, extraction, serialization, HTTP, SQL,
network and concurrent load excluded. Non-isolated single-machine in-process measurements.
Synthetic casting cores retain digits; Scale→Scxle edits a removed wrapper, not retained
identity. Its hit gate prevents empty-only timing claims, but is not genuine core-typo proof.

All quality/safety/cost gates apply together. No closest-winner or threshold/cap/policy tuning.
FAIL preserves v2 and blocks final authoring/T49. PASS only permits a committed experimental
artifact before separately owner-reviewed unseen final questions; no default activation.
