# Final-v2 owner approval and family-label freeze

Date: 2026-09-14. Scope: Lite IBR-T4 only. Label construction/owner-target confirmation PASS;
new final model quality/runtime closure NOT EVALUATED. No final-v2 retrieval or scoring performed.

The owner stated `首先驗證對象沒有問題` in the full recorded question about colors/features.
After explaining that105 questions assess casting/family retrieval, not complete variant accuracy,
the owner replied `沒有問題，請繼續下一步`. Those actual excerpts and the scope sentence are
recorded in `data/evaluation/family-retrieval-v2/approved/owner-decisions.json`. This is an attributable
visible-conversation journal, not signed identity proof or a claim of105 individual manual labels.
`recorded_at=2026-09-14T16:36:32Z` is recording time; unavailable message timestamp is null.

Immutable query SHA:
`b23b69912c678c027461c96eb23f113484c5a8ed6218c06d90026704abe5102b`.
Its committed baseline is `8f2891882f2836bfe492c7404e01654dea8b9fd9`, after winner `a9a3730`.
Full query/case/proposed-reference hashes, actual conversation and registry-derived expected
targets bind105 approvals to that precise pack. Approval does not promote Wiki releases to products.

The new `family_retrieval_final_v2_labels.py` and builder exclusively publish a complete `approved/`
child directory, leaving all original question/source bytes and historical pending flags untouched.
Three immutable JSON artifacts:

| File | SHA-256 |
|---|---|
| owner-decisions.json | a1ea2e8199c8082398e8895f29397dae7ac292760a4d92b67f31ef1a3f877296 |
| benchmark.json | ebb36e3a9fee2778076c317d0bc0f9848403c3363933a8ca9f8cbba5e271e29f |
| benchmark-manifest.json | 0cc7ab41828d72b1fdcb6337786ddffb36ab660225b2fe887213d6e5460fc312 |

84 positives use review-family ID/UUID,42 paired groups;4 merges use provisional casting ID/UUID
and forbid materializing their source family;7 holds forbid the excluded family but allow other
valid candidates;10 unrelated queries expect zero candidates. Merge answers intentionally do not
select one provisional release UUID. All original questions,84/4/7/10 counts,42/42 styles and
inherited gates remain unchanged, including family coverage over42 groups, not84 positive rows.
No colors, wheels or tampo labels are invented. The broader variant-data/evaluation gap persists.

Validation reconstructs exact labels from frozen inputs, checks type-sensitive metadata/full
case/source hashes, and rejects partial approvals, changed queries, altered targets/gates/scope,
stale builders and boolean-to-integer substitutions. Repeat freeze preserves bytes/timestamps;
simulated write failure publishes no partial approved directory. Commit precondition additionally
compares all approved files and both builders with the benchmark commit, without running retrieval.

Actual verification:28 new focused label tests;50 combined query/label tests PASS. Full suite379
PASS/no skips with one pre-existing Starlette/AnyIO BlockingPortal deprecation warning. First full
invocation without PYTHONPATH had378 pass/1 module-resolution subprocess failure; corrected
PYTHONPATH=src invocation passes379 without product-code edits. An initial Node command used the
wrong UI path and failed; `node --check ui/app.js` passes. Focused Ruff F/I, isolated strict MyPy,
Python compilation, v4 development JSON/Markdown, protocol and original-v1 benchmark/Markdown
reproduction PASS. Historical FAIL reports remain intact. No fresh Docker/HTTP/SQL/load measurement.

```bash
PYTHONPATH=src .venv/bin/python -m pytest
PYTHONPATH=src .venv/bin/python scripts/build_family_retrieval_benchmark_v2.py --check
PYTHONPATH=src .venv/bin/python scripts/build_family_retrieval_benchmark_v2.py --check-committed
```

Uncommitted benchmark rejection and modified-builder rejection are unit-tested; the actual precommit
CLI also rejects with `benchmark must be committed before scoring`. Actual committed verification
is a required handoff/T5 precondition. Next: T5 one final score with raw ranks preserved,
then full/runtime closure. A final FAIL cannot be tuned away. Defaultv2/T49/real SQL expansion gated.
