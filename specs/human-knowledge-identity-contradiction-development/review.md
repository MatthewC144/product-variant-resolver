# QA review — Human Knowledge candidate-specific identity contradiction v1

Date: 2026-09-21. Verdict: **implementation PASS; policy selection FAIL**.

## Coverage

| Requirement | Evidence | Result |
|---|---|---|
| HIC-R1 | Source and manifests name only committed public inputs; `private_local_artifacts_read` is false | PASS |
| HIC-R2–R3 | Frozen 12-positive/12-negative pack, 12 distinct positive documents, four positive and four negative challenge groups with three cases each | PASS |
| HIC-R4–R5 | Deterministic identity span, ordered one-to-one alignment, residual atoms, numeric conflicts, reason codes, and casting/alias-only evidence | PASS |
| HIC-R6 | Seven-policy protocol, 0.75 secondary rule, source order, hashes, gates, and winner ordering frozen before retrieval | PASS |
| HIC-R7 | Exactly 24 Top-5 calls produced 24 label-blind rows and 42 candidates; old 223 and v4 22 rows were rescored without retrieval | PASS |
| HIC-R8 | Existing, v4, new-positive, new-negative, retrieval-error, and contradiction-error gates are reported for every policy | PASS |
| HIC-R9 | All seven policies are ineligible; deterministic selection persists `winner: null` and authorizes no next-stage use | PASS |
| HIC-R10 | Freeze/collect/score reruns are unchanged; installed CLI `--check` independently recomputes a valid null result | PASS |
| HIC-R11 | No API, Dual RAG runtime, PostgreSQL, canonical, release, UUID, or physical-feature behavior changed | PASS |

## Findings

Implementation and evidence integrity pass. Pack and protocol were frozen before retrieval, the raw
artifact contains no expected or label key, every candidate maps back to a public corpus UUID, and
all artifact/source hashes remain stable. The frozen development source SHA-256 is
`167c03a5e19fae47eb867b8101c26f1c5bf49ca2c80fb2eb9a4e8bfa0660825f`.

Product eligibility fails. `baseline-anchor` preserves 168/168 existing positives, 10/10 v4
positives, and 12/12 new positives, but leaves 11/12 v4 and 10/12 new absent identities nonempty.
The strictest useful setting, `contradiction-050`, reduces both negative sets to 1/12 nonempty but
also falls to 164/168 existing positives, 9/10 v4 positives, and 11/12 new positives. The looser
1.00–1.50 settings preserve the two new positive sets but still lose one existing positive and leave
five to seven negative cases nonempty. No frozen policy satisfies all exact gates.

Eighteen focused tests, 52 related regression tests, and all 788 repository tests pass. Targeted
Ruff/format, MyPy, compileall, installed-wheel CLI help, two installed CLI integrity checks, and
`git diff --check` pass. The only warning is the existing Starlette/AnyIO deprecation warning and is
unrelated to this feature.

## Carry forward

Do not run another private evaluation or activate this policy. The public experiment shows that the
current deterministic alignment and scalar bilateral-residual thresholds improve negative
rejection but do not fully separate legitimate shorthand from wrong-model evidence. Any next
attempt requires a new versioned public design and newly frozen evidence; v1 source, raw rows, and
selection must remain immutable. Runtime work remains blocked until a future public policy passes
every recall and safety gate and then passes a separately designed private shadow evaluation.
