# Human Knowledge anchored compatibility admission selection

Public-development selection only; private evaluation and runtime are unchanged.

| Configuration | Secondary coverage | Eligible | Old R@5 | New required | Forbidden cases | Admitted | Abstained |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 0.0000 | yes | 168/168 | 24/24 | 18/24 | 329 | 0 |
| secondary-033 | 0.3333 | yes | 168/168 | 24/24 | 16/24 | 316 | 13 |
| secondary-040 | 0.4000 | yes | 168/168 | 24/24 | 8/24 | 282 | 47 |
| secondary-050 | 0.5000 | yes | 168/168 | 24/24 | 7/24 | 274 | 55 |
| secondary-060 | 0.6000 | yes | 168/168 | 24/24 | 2/24 | 237 | 92 |
| secondary-067 | 0.6667 | yes | 168/168 | 24/24 | 2/24 | 234 | 95 |
| secondary-075 | 0.7500 | yes | 168/168 | 24/24 | 0/24 | 212 | 117 |
| secondary-100 | 1.0000 | no | 167/168 | 24/24 | 0/24 | 209 | 120 |

## Selection

Selected **secondary-075** with secondary coverage `0.75` for a new versioned private shadow evaluation only.

The selection is not active in the API or Dual RAG runtime.
