# AI eval — local review-family anchored admission v2

## Verdict

**FAIL.** The frozen post-retrieval policy preserves private positive retrieval quality but fails the
hard-negative safety gates. It is not eligible for runtime activation.

## Dataset and leakage disclosure

The owner-private evaluation contains 20 previously frozen cases over five local review families:
15 non-exact positives and five near-confusable hard negatives. This v2 evaluation reuses immutable
v1 raw Top-5 output and executes zero retrieval calls. The `secondary-075` policy was selected using
separate public development data before private scoring. Private case text, labels, identities,
coverage, ranks, and results are excluded from Git.

## Rubric assessment

| Rubric area | Result | Evidence and boundary |
|---|---|---|
| Dataset disclosure | PASS | Version, 15/5 counts, five-family scope, hash chain, and owner-private limitation are recorded. |
| Leakage control | PASS for this attempt | Policy frozen on public development before private scoring; no private tuning or reretrieval. |
| Retrieval/positive ranking | PASS within bounded set | Recall@5 15/15, Recall@1 13/15, family coverage 5/5. |
| Hard-negative safety | FAIL | Two forbidden-family hits remain; both are source rank 1 and survive the anchor. |
| Reranker/admission value | PARTIAL | Forbidden hits decrease from three to two, but the zero-hit gate is not met. |
| Abstention/reliability | FAIL for release claim | 18/44 candidates are abstained, yet false admission remains on 2/5 hard negatives. |
| Latency | NOT EVALUATED | Offline policy scoring reuses raw evidence; no runtime latency claim is made. |
| Failure safety | PASS | Zero retrieval/admission errors; tamper and partial-state checks fail closed. |
| Runtime boundary | PASS | Runtime/API/PostgreSQL/canonical/release/color effects all remain zero. |

## Decision

Do not integrate the policy. Return to public development and design a rank-1 compatibility or
confidence mechanism. The private failures cannot be converted into development labels or special
cases. A future policy needs another pre-frozen, versioned private gate.
