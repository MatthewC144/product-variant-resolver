# Human Knowledge identity-contradiction selection

Public-development selection only; private evaluation and runtime are unchanged.

| Configuration | Eligible | Existing R@5 | V4 anchors | V4 missing nonempty | New positives | New absent nonempty |
|---|---:|---:|---:|---:|---:|---:|
| baseline-anchor | no | 168/168 | 10/10 | 11/12 | 12/12 | 10/12 |
| numeric-only | no | 167/168 | 10/10 | 10/12 | 12/12 | 10/12 |
| contradiction-050 | no | 164/168 | 9/10 | 1/12 | 11/12 | 1/12 |
| contradiction-075 | no | 165/168 | 9/10 | 1/12 | 11/12 | 2/12 |
| contradiction-100 | no | 167/168 | 10/10 | 6/12 | 12/12 | 5/12 |
| contradiction-125 | no | 167/168 | 10/10 | 6/12 | 12/12 | 5/12 |
| contradiction-150 | no | 167/168 | 10/10 | 7/12 | 12/12 | 5/12 |

## Selection

No configuration passed every frozen recall and contradiction-safety gate.

The selection is not active in the API or Dual RAG runtime.
