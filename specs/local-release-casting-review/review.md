# Local release casting review queue — QA review

Date: 2026-09-17. Mode: Lite / Lean Industrial. Verdict: **PASS**.

## Coverage

| Requirement | Verification | Result |
|---|---|---|
| LCR-R1 | Local staging/catalog inputs; queue policy and report assert zero network requests | PASS |
| LCR-R2 | Negative tests reject changed review status, usage, canonical UUID, and color | PASS |
| LCR-R3 | Synthetic and owner-data tests preserve raw labels/IDs inside private clusters | PASS |
| LCR-R4 | Tests exercise both, fixture-only, human-only, and no-exact classes | PASS |
| LCR-R5 | Every cluster remains held, non-promotable, and without canonical UUID | PASS |
| LCR-R6 | Accent-normalized collision test retains both labels and raises review priority | PASS |
| LCR-R7 | Reordered inputs reproduce identical queue; CLI `--check` reproduces stored bytes | PASS |
| LCR-R8 | Public manifest/report expose counts and hashes only; exact aggregate asserted | PASS |

## Results

- Focused tests: 11/11 PASS.
- Full repository tests: 640/640 PASS; one existing Starlette/AnyIO deprecation warning.
- Changed-file Ruff F/I and format: PASS.
- Strict MyPy for the new module: PASS.
- Compileall, deterministic CLI `--check`, and `git diff --check`: PASS.

The owner-data integration found 1,763 observations, 678 raw labels, 676 normalized review clusters,
and two normalization collisions. Candidate classes are 1 both-source, 2 synthetic-fixture-only,
40 human-draft-only, and 633 without an exact candidate. These account for 1/8/126/1,628 source
observations respectively. Approved links, promotions, reviewed colors, SQL writes, and network
requests remain zero.

## Findings and carry-forward

No release-blocking finding remains. The main semantic risk is interpreting an exact normalized
name as verified identity: the canonical fixture is synthetic, the human catalog is non-canonical,
and neither proves release-level variant attributes. The next milestone should prepare a small,
explicit owner-review batch from the queue and record decisions separately; it must not mutate this
queue, infer color, or promote all 43 exact candidates automatically.
