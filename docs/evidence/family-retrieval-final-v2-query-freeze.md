# IBR-T4 preparation — final-v2 query-only handoff

Date: 2026-09-14. Mode: Lite, no subagents. Preparation engineering: PASS.
Owner approval, labels, final retrieval/score, whole T4/T5/T49: PENDING / NOT EVALUATED.

## Authoritative owner handoff

[Read every frozen query and intended target](../../data/evaluation/family-retrieval-v2/owner-review.md).
Query-pack SHA-256: `b23b69912c678c027461c96eb23f113484c5a8ed6218c06d90026704abe5102b`.
Manifest SHA-256: `cf4405da39f39e704746510174923cfe3c4c2474470630d163bb7293867a1203`.
Review SHA-256: `c0753443d03c3db9de01319b868d779049ad330f702eed16a070fa53170e7cc7`.
Freeze time: `2026-09-14T14:15:13Z`; qualified winner commit `a9a3730` is earlier
(`2026-09-14T10:04:23-04:00` = `14:04:23Z`).

Git ancestor/byte checks confirm selected artifact, runtime/evaluator/protocol/corpus inputs and old
dedup questions match the winner commit. That commit has no new final query pack. The authoring
module/script and input checksums are now frozen separately; no runtime/scorer/v3 source changed.
Only old query texts—not old final labels/results—are read for reuse rejection. Existing historical
scored reports are checked separately as regressions, not authoring or final-selection inputs.

## Composition and leakage limits

Exactly 105 questions: 84 positives (42 approved families × marketplace/lexical pair), 4 merge,
7 hold, 10 unrelated. Registry references are proposed relevance-review targets, **not** generated
expected labels or retrieved candidates. Every pair appears in the owner table, with case hash
prefix; the manifest retains all 105 full case checksums and pack/review/source bindings.

Static audit: 304 old questions (105 v1 + 199 dev), 561 indexed/governance/human-label strings,
zero normalized/compact duplicates or old/indexed exact reuse, zero nonempty previous question-core
reuse, all 42 family pairs and all 4/7 controls covered, ten nonvehicle terms with zero whole-token
corpus overlap. These checks do not prove semantic paraphrase independence or lack of all author bias.
The author knows prior development/policy, uses familiar families and writes synthetic questions.
Output-blind means no retrieval/result of **these 105 new questions**, not unseen family/independent
author/population sampling. No live Wiki/marketplace fetch or new catalog ingestion took place.

The unrelated words are ordinary nonvehicle nouns (e.g. quinoa, origami, thermocouple), not selected
by character-score trials. Static zero whole-token overlap does not guarantee zero character matches;
the final no-candidate gate is still a genuine requirement after approval. Hold controls prohibit the
unapproved review-family identity, not all possible provisional-variant candidates.

## Pre-approval correction preserved

Initial metadata named coverage `positive_coverage`, which could be mistaken for query-response
coverage. The inherited evaluator instead computes `family_coverage_at_5` over 42 groups (a family
is covered if at least one of its two positive questions finds its target at K=5), threshold0.90.
The error was found by reading its gate/formula before owner handoff, labels or retrieval. The draft
was moved recoverably to `family-retrieval-v2-superseded-draft-01`; its pack/manifest/review and exact
author-source snapshots remain intact. `SUPERSEDED.md` explicitly excludes approval/scoring use.

The same 105 case objects were re-frozen with the correct metric name; no query, threshold, policy,
model or candidate output drove the correction. Draft SHA `e52902e72e057d125e984eae81bfe78bf1859a8d7fed366f2277f734510c4d14`
is **not** the owner-approval checksum. Use only the authoritative `b23b6991…` pack above.

## Verification and safe boundary

22 focused new tests / 351 full repository tests pass, no skips; one existing Starlette/AnyIO warning.
Focused RuffF/I and isolated strict MyPy authoring module, compilation, whitespace, Node syntax and
default/PostgreSQL-profile Compose checks pass. Final-v2 freeze and old protocol/dev/v3/v1 report
checks pass unchanged. No fresh Docker runtime or model-quality claim is produced in this step.

Tests forbid new retrieval and old label/result reads during authoring; check committed provenance,
complete pairs/controls, copied normalized/compact/core/indexed strings, invalid identity/style/
counts/labels, metadata/source/review checksums, timestamps and repeat-freeze byte/time preservation.
A private staged directory publishes pack+manifest+review together; simulated write failure cleans
only owned temporary files and exposes no partial final directory. Genuine frozen-pack and preserved
draft snapshots/question equality checks pass. Temporary fixture Git provenance is mocked only after
the separate genuine committed-winner test; this is not a fake owner approval.

```bash
PYTHONPATH=src .venv/bin/python scripts/author_family_retrieval_query_pack_v2.py --check
PYTHONPATH=src .venv/bin/pytest -o addopts='' -q tests/evaluation/test_family_retrieval_final_v2.py
PYTHONPATH=src .venv/bin/pytest -o addopts='' -q
```

Current directory contains only query-pack, manifest and owner review. No owner-decisions, expected
labels, benchmark, raw final candidates or score exists. Approval/label/scorer implementation is
intentionally deferred; the current phase guard rejects access even if someone drops an unvalidated
approval file. **STOP for explicit owner confirmation of all frozen pairs/checksum.** Then a separate
approved phase may record approval, freeze attributable labels and commit benchmark before one final
score. Default v2, independent-final/runtime closure and T49/3,000-real-row expansion remain gated.
