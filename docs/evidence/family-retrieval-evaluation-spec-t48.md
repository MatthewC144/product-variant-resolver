# Family Retrieval Evaluation T48 — Specification Evidence

> Mode: Lite / Lean Industrial
>
> Status: Confirmed; T48.1 contract implementation complete
>
> Date: 2026-09-11

## Problem converted into a testable boundary

T47's 42/42 Top-5 result uses each accepted family's own brand and display name as the query. It is
valid wiring evidence but cannot reveal whether the retriever handles seller noise, abbreviations,
spacing changes, punctuation, or misspellings. T48 defines a separate test-only challenge set whose
queries are frozen before any retriever output is viewed and whose labels require a separate owner-
approval artifact.

The source audit found two boundaries that the specification preserves. The 2025 Fandom normalized
rows declare `staging_only_not_evaluation_or_canonical`, and the T47 projection explicitly excludes
`evaluation_ground_truth`. Neither is silently repurposed as scored labels. Identity references may
define the review question, but query wording must be separately composed and owner-confirmed.

## Feasibility measurements

The current projection contains 42 unique normalized family names: 4 single-token, 15 two-token,
and 23 with three or more tokens. The single-token names are Haulerback, Crescendo, Bogzilla, and
Draftnator. They are deliberately retained in lexical-variation challenges because the current
retriever's shared-token requirement may fail on a pure misspelling; hiding those cases would bias
the evaluation.

The accepted registry has 79 held release references across the 42 new families, 9 references under
the 4 accepted merges, and 12 under the 7 holds. These counts support full control coverage, but the
release records remain provenance rather than evaluation queries or variant truth.

The proposed Lite benchmark contains 105 cases:

| Case class | Count | Purpose |
|---|---:|---|
| Positive `marketplace_noise` | `42` | One separately written noisy-wrapper query per accepted family |
| Positive `lexical_variation` | `42` | One non-exact phrase/abbreviation/typo challenge per family |
| Accepted merge controls | `4` | Confirm existing provisional-variant families, not duplicate review families |
| Held-family controls | `7` | Confirm forbidden family identities stay unmaterialized |
| Unrelated no-overlap controls | `10` | Confirm the shared-token eligibility boundary returns no candidates |
| **Total** | **105** | All cases fixed to the one-time test split |

## Precommitted decision

The quality gates are written before the dataset is authored or scored: positive Recall@5 at least
0.85, Recall@1 at least 0.65, MRR@5 at least 0.75, each positive style Recall@5 at least 0.75,
family coverage@5 at least 0.90, all four merge controls found within Top-5, zero forbidden family
hits, and zero non-empty unrelated results.

A valid report below those gates must say FAIL. The same v1 holdout cannot then be used both to tune
and to prove the replacement retriever; final evaluation of a changed system requires a newly
authored version. This makes failure informative and prevents threshold/model selection from
leaking test labels.

## Scope and baseline evidence

T48 changes no runtime code, data, or evaluation claim in this specification step. The baseline
remains T47's 184/184 passing suite, 142 typed documents, frozen canonical fixture metrics, and
debug-only/no-PostgreSQL boundary. The specification provides sixteen EARS requirements, a complete
design, five ordered implementation tasks, traceability for every requirement, security/privacy
notes, error behavior, and explicit alternatives.

A fresh host rerun passed 184/184 tests in 1.637 seconds. Static specification checks found exactly
16 FRE requirement headings, confirmed every requirement appears in task traceability, verified all
required design sections, and passed `git diff --check`. The only suite message is the previously
documented non-failing Starlette legacy-`httpx` environment warning.

The project owner's request to proceed confirmed the requirements, design, and ordered tasks. T48.1
now implements the strict benchmark contract and its negative tests; detailed build evidence is in
`family-retrieval-benchmark-contract-t48-1.md`. No retrieval may run while the formal query pack is
authored and independently frozen in T48.2.
