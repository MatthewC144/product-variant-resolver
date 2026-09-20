# Local release review-family retrieval evaluation — evidence

Date: 2026-09-19. Lite / Lean Industrial. Verdict: **FAIL; runtime integration blocked**.

The private benchmark was frozen against projection SHA-256
`32644f9c5b91039fde7b7a9586f8a6bf9479ea7c6878661d329ea53bed4207d8` before retrieval. It contains
15 non-exact positive questions—three for each local family—and five near-confusable hard negatives,
one per family. Queries and expected labels are separate private files. The collector opened only the
query pack, executed every query once against the current 142 Human Knowledge documents plus five
local shadow candidates, wrote raw results, and only then loaded expected labels for scoring.

The frozen Human Knowledge RAG v4 configuration used a 0.5 character floor, 1.0 character RRF weight,
and 192-dimensional `hashing-v1` dense vectors. Positive Recall@5 was `1.0` (15/15), Recall@1 was
`0.8667` (13/15), and family coverage@5 was `1.0` (5/5). These three positive gates passed and no
retrieval error occurred. The hard-negative gate required exactly zero forbidden local-family hits;
three occurred, so the overall result is FAIL. No question was edited, no parameter was tuned, and no
second retrieval run was performed after seeing the failure.

The failure is useful: the candidate corpus is discoverable, but the present character/exact/dense
fusion can still admit an overly broad family when a query shares manufacturer, numeric model, or
generic body-style wording. The benchmark is too small to estimate population accuracy, and family
retrieval says nothing about color, wheel, tampo, packaging, year-specific release, or canonical
product correctness.

Private query text, targets, candidates, ranks, and per-case results remain under the ignored owner
data tree. The committed public report exposes only hashes, configuration, counts, aggregate metrics,
gates, limitations, and zero downstream effects. Runtime documents added, canonical promotions,
reviewed colors, PostgreSQL writes, API changes, and network requests are all zero.

Thirteen focused tests cover frozen counts, non-exact positives, fixed gates, label-blind collection,
exactly-once failure capture, deterministic scoring, privacy, no rerun, partial output rejection, and
raw-rank tamper detection. The full-repository result and static checks are recorded in the project
log. The next implementation must be a new, development-only false-positive mitigation experiment;
this failed benchmark remains immutable test evidence and cannot be used for tuning.
