# T45 Review-Family Materialization Specification — Evidence

## Outcome

The Lite specification is complete and awaiting project-owner confirmation. It consists of
testable requirements, a concrete data/CLI design, and traceable implementation tasks. No product
code, catalog, runtime, evaluation, or database data changed.

## Input inspection

The proposed contract was checked against the actual final queue and current human-backed catalog:

| Check | Result |
|---|---:|
| Queue status | `adjudicated` |
| Completed / pending families | `53 / 0` |
| Accepted new / merge / hold families | `42 / 4 / 7` |
| Create / merge / hold source rows | `79 / 9 / 12` |
| Total held source rows | `100` |
| Existing human-backed families | `97` |
| Exact normalized collisions for accepted creations | `0` |
| Current readable-ID collisions among accepted creations | `0` |

The absence of current collisions is supporting evidence, not an identity guarantee. The design
uses the immutable `family_review_id` plus a fixed UUIDv5 namespace so later names and larger imports
cannot silently redefine identity.

## Gate coverage

- `requirements.md` contains thirteen EARS-style, independently testable requirements.
- `design.md` covers overview, architecture, interfaces, data models, identity/alias rules, build
  algorithm, error handling, security notes, testing, and deferred integration.
- `tasks.md` separates implementation, validation, and QA/documentation work and maps each task to
  the RFM requirements.
- Decision D30 records the chosen separate-registry design, rejected alternatives, consequences,
  and deferred work.
- `docs/PROJECT-LOG.md` records the problem, exact affected areas, method selection, trade-offs,
  decision status, evidence, risks, and next step.

## Safety boundary

The proposed registry will contain family-level entities and links only. All 100 Wiki source rows
remain held release references; no placeholder provisional variant is allowed. Runtime retrieval,
the API/debug schema, `human_backed_catalog.json`, canonical identities, calibration/evaluation
data, migrations, and PostgreSQL stay outside T46.

## Next gate

G1* remains awaiting the project owner's confirmation of all three spec documents. After that
confirmation, T46.1 can implement the registry builder. The executable baseline remains the T44
159/159 passing suite because T45 makes documentation changes only. A fresh host rerun after the
specification edits passed 159/159 in 1.418 seconds; `git diff --check`, all required design-section
checks, and explicit task coverage for all thirteen RFM requirements also pass.
