# Human Knowledge rank-1 anchor confidence v4 — evidence

Date: 2026-09-21. Lite / Lean Industrial. Verdict: **experiment valid; no policy qualified**.

The public pack contains ten known-correct rank-1 anchors with identity coverage below 0.75 and
twelve queries naming castings absent from the committed 142-document corpus. Pack SHA-256 is
`a21d57394fab99f49513c44dfefa9deb171b69441a3ffb2cef087f6e775adf0c`. Protocol SHA-256 is
`75dedf6fc15b0711aeb667d1e538d9226a66b6090eba22ef0694a94a35713d40`. Both were written before
retrieval and record that no private artifact was read.

One retrieval pass made exactly 22 Top-5 calls and produced 42 candidates. Ten fixed rank-1
thresholds then reused those bytes; ranks 2–5 continued to require 0.75 identity-token coverage.
All settings also re-scored the existing 223 public rows.

| Rank-1 threshold | Eligible | Existing R@5 | Anchor positives | Missing identities nonempty |
|---:|---:|---:|---:|---:|
| 0 | no | 168/168 | 10/10 | 11/12 |
| 0.50 | no | 168/168 | 10/10 | 11/12 |
| 0.55 | no | 168/168 | 10/10 | 10/12 |
| 0.575 | no | 168/168 | 10/10 | 10/12 |
| 0.60 | no | 168/168 | 10/10 | 10/12 |
| 0.61 | no | 168/168 | 10/10 | 10/12 |
| 0.625 | no | 167/168 | 9/10 | 10/12 |
| 0.65 | no | 167/168 | 9/10 | 9/12 |
| 0.70 | no | 167/168 | 9/10 | 5/12 |
| 0.75 | no | 167/168 | 9/10 | 4/12 |

The result SHA-256 is
`e8d51e24150889059b0ac8aa881be48deae836302f7865b6c1d62095d25dd502`. The null winner is not a
software failure: it is the deterministic outcome required when no setting satisfies every gate.
The experiment shows that character similarity and token coverage overlap too heavily between valid
typos and same-manufacturer/model-neighbor errors for their maximum to be a safe admission score.

No private query, label, candidate, rank, or path was used for tuning. The API, Dual RAG runtime,
PostgreSQL, canonical catalog, release review, and color behavior are unchanged. Nine focused and
770 full tests pass.
