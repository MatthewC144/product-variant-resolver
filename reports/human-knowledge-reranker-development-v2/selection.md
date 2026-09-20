# Human Knowledge candidate-relative reranker selection

Development selection only; runtime and private final evaluation are unchanged.

| Configuration | Weight | Eligible | Existing R@5 | Existing R@1 | New required | Forbidden cases | Safety |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 0.00 | yes | 168/168 | 165/168 | 24/24 | 18/24 | 0.2500 |
| penalty-005 | 0.05 | yes | 168/168 | 165/168 | 24/24 | 18/24 | 0.2500 |
| penalty-010 | 0.10 | yes | 168/168 | 165/168 | 24/24 | 18/24 | 0.2500 |
| penalty-025 | 0.25 | yes | 168/168 | 165/168 | 24/24 | 18/24 | 0.2500 |
| penalty-050 | 0.50 | yes | 168/168 | 165/168 | 24/24 | 18/24 | 0.2500 |
| penalty-100 | 1.00 | yes | 168/168 | 165/168 | 24/24 | 18/24 | 0.2500 |
| penalty-200 | 2.00 | yes | 168/168 | 165/168 | 24/24 | 18/24 | 0.2500 |

## Selection

The frozen rule returned **baseline**, but it does not improve forbidden-case safety over baseline; no mitigation qualified.

The selection is not active in the API or Dual RAG runtime.
