# Canonical Authority Review v1 — Final evidence

Date: 2026-10-04
Mode: Lite / Lean Industrial
Verdict: **ENGINEERING PASS / DATA GATE PASS / RHB-T5 UNAUTHORIZED**

## What the milestone established

Canonical Authority Review v1 converted one already checked-in, attributed 100-row community
snapshot into a bounded, output-blind human-review workflow. It did not crawl, call a live API,
consult resolver output or infer missing variant fields. The workflow produced 20 distinct
`approved_exact` catalog-v2 UUIDs across seven same-casting multi-release families.

The claim tier is deliberately narrow: values are exact relative to the frozen Hot Wheels Wiki
community revision `790665`, not Mattel/manufacturer-certified truth. Color and edition are
unsupported by the snapshot and remain null.

| Final result | Value |
|---|---:|
| Approved exact variants | 20 |
| Distinct canonical UUIDs | 20 |
| Qualifying families | 7 |
| Minimum variants / families | 20 / 4 |
| Exact / family shortfall | 0 / 0 |
| CAR-T5F result | `eligible_for_rhb_t4_reaudit` |
| Versioned RHB-T4 result | `passed_exact_authority_gate` |
| Network requests | 0 |
| Resolver output / labels consulted | false / false |
| RHB-T5 authorized | false |

## Requirement evidence map

| Requirements | Durable evidence |
|---|---|
| CAR-R1, R2, R6 | Source decisions and manifest; strict source validator; frozen normalized row/revision/license bindings |
| CAR-R2, R3 | Catalog proposal/application artifacts; private output-blind packet; safe packet manifest |
| CAR-R4, R5 | Append-only review events; seven T5-G1 and seven T5-G2 owner authorizations/attestations; transition validators |
| CAR-R7 | Stable JSON/hashes, atomic builders, rollback tests and unchanged replays |
| CAR-R8 | CAR-T5F authority bundle/manifest: 20 unique variants, seven families, zero shortfalls |
| CAR-R9 | Separate CAR-T6 authority/manifest beside the unchanged historical RHB-T4 blocked checkpoint |
| CAR-R10 | 317 focused tests, 1,379 full tests, negative mutation and partial-write coverage |
| CAR-R11 | Final QA review, this evidence, AI eval, Project Log and bounded Portfolio Guide claims |

## Verification

- `317` focused authority, CAR-T6 and historical RHB-T4 tests passed.
- `1,379` full-repository tests passed with one pre-existing Starlette/AnyIO deprecation warning.
- CAR-T1 Source Gate: `valid`.
- CAR-T6 and historical RHB-T4 deterministic checks: `unchanged` / `unchanged`.
- Ruff check and format check passed across 20 scoped implementation/test files.
- Strict MyPy passed on nine production/CLI modules and the CAR-T6 test: 10 files, no issues.
- Compileall, critical JSON parsing, actual-owner-response privacy scan and whitespace checks passed.
- Expanded strict MyPy over all legacy authority tests exposed 22 existing test-only diagnostics in
  three modules. This is recorded technical debt; no repository-wide test-type PASS is claimed.

## Key technical decisions

1. **Source context is not identity authority.** Candidate selection could use family context, but
   each exact row needed its own catalog UUID/hash and field-level evidence.
2. **Two owner Gates prevent accidental promotion.** `staged→reviewed` and
   `reviewed→approved_exact` used separate exact responses and attestations.
3. **Unsupported fields stay unknown.** `2nd Color` remained context; it never became a color name.
4. **Public evidence is hash-based and private review text stays local.** Public artifacts contain
   safe records/counts/digests; verbatim approvals remain in ignored `0600` ledgers.
5. **Historical audits are append-only.** The honest zero-authority RHB-T4 block was preserved, and
   CAR-T6 created a new versioned PASS rather than rewriting history.

## Failures and fixes retained as evidence

- Initial CAR-T1 QA found permissive inner schemas and removable attribution despite valid outer
  hashes. Strict semantic validation and mutation tests fixed the issue; the original FAIL remains
  in `review.md`.
- CAR-T6 tests found a datetime object being hashed before JSON normalization. The manifest now
  hashes a whole-second UTC ISO-8601 string.
- Final privacy review found that a test fixture duplicated the real approval sentence. It was
  replaced with an explicit `TEST-ONLY` response, and the final relevant suites passed again.

## Remaining boundary

CAR v1 establishes a reviewable authority input, not resolver accuracy or benchmark readiness. The
next possible benchmark task is RHB-T5 output-blind query authoring, which remains prohibited until
a separate owner Gate. No current result supports broad marketplace coverage, manufacturer truth,
or a production-quality claim.
