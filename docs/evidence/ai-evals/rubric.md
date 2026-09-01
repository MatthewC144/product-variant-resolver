# Resolver Output Evaluation Rubric

This rubric gates claims about AI/ranking output for the Lite MVP. A release claim passes only when
every required item has traceable evidence; a missing item is `not evaluated`, not an implicit pass.

| Criterion | Pass condition | Required evidence |
|---|---|---|
| Dataset disclosure | Dataset version, construction method, counts, split, and synthetic/curated limitation are visible. | Manifest plus report disclosure. |
| Leakage control | Casting families do not cross query splits; calibration uses train and policy selection uses dev; test-label access is false until evaluation. | Split validator and artifact metadata. |
| Retrieval | Recall@25 on applicable matched test cases is `>=0.95`. | Raw retrieved count and matched count. |
| Ranking | Top-1 is `>=0.80` and hard-negative accuracy is `>=0.75`. | Per-stage raw target ranks and hard-negative counts. |
| Reranker value | Gain over RRF is `>=0.05`, or a data-backed default-path omission is documented. | Same-case RRF/reranker comparison and decision record. |
| Abstention/reliability | Precision is `>=0.90`, false-match rate is `<=0.10`, and coverage is `>=0.50`. | Raw predicted/correct/false/non-match/matched counts. |
| Latency honesty | Candidate K, hardware/runtime, warm-up, sample count, method, and excluded boundaries are disclosed; limited fixture p95 is `<=1500 ms`. | Raw latency samples and scope statement. |
| Failure safety | Missing required data/provider and retriever failures do not fabricate a match; default response omits debug internals. | API/service tests and manual QA checks. |

## Claim rules

- Fixture metrics may be described only as synthetic/curated MVP results.
- `hashing-v1` must not be called a neural embedding model.
- `heuristic-v1` must not be called a cross-encoder.
- In-process ASGI timing must not be called Docker, TCP, database, concurrency, or production
  latency.
- Static Compose validation must not be called a successful container run.
- A QA secret scan is not a formal security review; a CPU smoke measurement is not a formal
  performance review.

The current scored record is [`fixture-v1.md`](fixture-v1.md).
