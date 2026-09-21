# Human Knowledge rank-1 anchor-confidence selection

Public-development selection only; private evaluation and runtime are unchanged.

| Configuration | Anchor threshold | Eligible | Existing R@5 | Prior required | Anchor positives | Missing nonempty |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0.000 | no | 168/168 | 24/24 | 10/10 | 11/12 |
| anchor-050 | 0.500 | no | 168/168 | 24/24 | 10/10 | 11/12 |
| anchor-055 | 0.550 | no | 168/168 | 24/24 | 10/10 | 10/12 |
| anchor-0575 | 0.575 | no | 168/168 | 24/24 | 10/10 | 10/12 |
| anchor-060 | 0.600 | no | 168/168 | 24/24 | 10/10 | 10/12 |
| anchor-061 | 0.610 | no | 168/168 | 24/24 | 10/10 | 10/12 |
| anchor-0625 | 0.625 | no | 167/168 | 24/24 | 9/10 | 10/12 |
| anchor-065 | 0.650 | no | 167/168 | 24/24 | 9/10 | 9/12 |
| anchor-070 | 0.700 | no | 167/168 | 24/24 | 9/10 | 5/12 |
| anchor-075 | 0.750 | no | 167/168 | 24/24 | 9/10 | 4/12 |

## Selection

No configuration passed every frozen recall and anchor-safety gate.

The selection is not active in the API or Dual RAG runtime.
