# T47 Family-Level Human Knowledge Specification — Evidence

## Outcome

The Lite requirements, design, and task plan were confirmed when the project owner requested the
next step. T47.1 has since created the separately evidenced family-knowledge projection; runtime
code, API schema, UI, configuration, PostgreSQL rows, calibration, and evaluation remain unchanged.

## Current-system inspection

- The current human-knowledge index contains 100 provisional-variant documents and reports
  `human-knowledge-hybrid-v1`.
- `HumanKnowledgeDocument` and `HumanKnowledgeCandidateDebug` currently require provisional variant
  IDs; this is why a typed family document is necessary instead of a placeholder variant.
- The second RAG already executes independently from canonical candidate ranking and only appears in
  debug output.
- T46 provides 42 accepted new families, 4 merge links, 7 hold exclusions, and 100 held release
  references. Its audit registry is explicitly excluded from direct runtime loading.

## Read-only feasibility simulation

The existing hashing embedding, sparse score, and RRF formulas were run in memory over the current
100 variant documents plus projected brand/name/alias text for the 42 accepted families.

| Check | Result |
|---|---:|
| Combined documents | `142` |
| Globally unique UUIDs | `142` |
| Exact brand + family-name queries recovered within Top-5 | `42 / 42` |
| Worst expected-family rank | `2` |
| Existing BMW M3 GT2 Neon Speeders variant rank | `1` |
| Runtime/data writes | `0` |

The Power Wheels Dune Racer hold query surfaced a different accepted family containing a shared
`racer` token. The held Power Wheels identity itself cannot appear because it has no projected
document. This observation is retained as a limitation: exact-name self-retrieval is suitable for a
wiring smoke test, but unrelated-token behavior requires T48's independent holdout evaluation.

## G1* coverage

- Sixteen EARS requirements cover projection, typed documents, retrieval, regression, holds/merges,
  canonical isolation, API/UI safety, readiness, observability, and scope boundaries.
- Design specifies interfaces, data models, configuration, retrieval flow, API union, health,
  observability, UI behavior, errors, security, testing, and deferred work.
- Four implementation tasks map all sixteen requirements to backend, frontend, QA, and documentation
  acceptance criteria.
- Decision D31 records the runtime-projection/unified-index choice, rejected alternatives, measured
  feasibility, the most likely quality failure, and deferred PostgreSQL/scale work.
- Project log records the executed analysis, affected code areas, technology/method choices,
  trade-offs, decision change, evidence, risks, and next step.

## Next gate

G1* was accepted by the project owner's request to execute the next step. T47.1 is complete; T47.2
now adds typed v2 retrieval, followed by discriminated API/UI integration and Lite QA.

A fresh complete host run passed 168/168 tests in 1.628 seconds. It emitted only the repository's
already documented, non-failing Starlette legacy-`httpx` TestClient deprecation warning. Static
validation also confirmed 16/16 requirement-to-task references, all required design sections, and
no whitespace errors.
