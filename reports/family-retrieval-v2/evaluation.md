# Final-v2 family retrieval

Verdict: **PASS** (family retrieval only).
No final-set tuning/default deployment/canonical or release-variant claim.

| Gate | Actual | Required | Result |
|---|---:|---:|---|
| family_coverage_at_5 | 1.000000 | >=0.9 | PASS |
| forbidden_family_candidates | 0.000000 | =0 | PASS |
| merge_recall_at_5 | 1.000000 | =1.0 | PASS |
| mrr_at_5 | 0.932540 | >=0.75 | PASS |
| positive_recall_at_1 | 0.916667 | >=0.65 | PASS |
| positive_recall_at_5 | 0.952381 | >=0.85 | PASS |
| lexical_variation | 0.904762 | >=0.75 | PASS |
| marketplace_noise | 1.000000 | >=0.75 | PASS |
| unrelated_nonempty | 0.000000 | =0 | PASS |

Counts: `{"covered_families": 42, "family_total": 42, "forbidden_family_candidates": 0, "merge_hits_at_5": 4, "merge_total": 4, "positive_hits_at_1": 77, "positive_hits_at_5": 80, "positive_reciprocal_rank_sum": 78.33333333333333, "positive_styles": {"lexical_variation": {"hits_at_5": 38, "total": 42}, "marketplace_noise": {"hits_at_5": 42, "total": 42}}, "positive_total": 84, "retrieval_errors": 0, "unrelated_nonempty": 0, "unrelated_total": 10}`

Diagnostic cost: `{"final_latency_has_no_new_acceptance_threshold": true, "p50_ms": 2.591583, "p95_ms": 6.945209, "percentile_method": "nearest_rank", "sample_count": 105}`

Abstentions: `{}`

## Case errors/misses

- `fr2-positive-18e55e067083dbd1-lexical_variation`: audy quatrro eighty-seven rally miniature; target rank=None; positive_target_missed_at_5; returned=[]
- `fr2-positive-1b2a4227b4e5decd-lexical_variation`: mercedez five-hundred-E saloon; target rank=None; positive_target_missed_at_5; returned=[]
- `fr2-positive-4d2de6db3d5bba63-lexical_variation`: crecsendo music inspired casting; target rank=None; positive_target_missed_at_5; returned=[]
- `fr2-positive-aab5350cb90d72ed-lexical_variation`: ford brnoco twenty-one SUV; target rank=None; positive_target_missed_at_5; returned=[]

## Limitations

- synthetic_same_family_questions_not_population_or_unseen_casting_accuracy
- prior_development_known_not_independent_author
- family_truth_not_release_variant_truth
- human_debug_only_canonical_authority_unchanged
- single_process_non_isolated_host
- hashing_v1_not_neural
- final_cost_diagnostic_not_fitted_gate_or_http_sql_latency
