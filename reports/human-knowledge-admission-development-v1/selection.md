# Human Knowledge admission-policy development selection

This is development selection only; runtime and private final evaluation are unchanged.

| Configuration | Coverage | Eligible | Existing R@5 | New required | Forbidden cases | Safety |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0.0000 | yes | 168/168 | 24/24 | 18/24 | 0.2500 |
| coverage-050 | 0.5000 | no | 167/168 | 24/24 | 7/24 | 0.7083 |
| coverage-067 | 0.6667 | no | 165/168 | 24/24 | 2/24 | 0.9167 |
| coverage-075 | 0.7500 | no | 159/168 | 23/24 | 0/24 | 1.0000 |
| coverage-100 | 1.0000 | no | 152/168 | 22/24 | 0/24 | 1.0000 |

## Selection

Selected development configuration: **baseline** 
with minimum identity-token coverage `0.0`.

The winner is not active in the API or Dual RAG runtime.
