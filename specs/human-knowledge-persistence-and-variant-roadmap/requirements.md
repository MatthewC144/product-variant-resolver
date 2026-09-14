# T49 — Human knowledge persistence and real-variant roadmap requirements

Date:2026-09-14. Mode:Lite. Status:DRAFT, owner confirmation required; no implementation authorized.
Upstream:IBR-T5 scoped family/runtime closure ataf27dfe. Originalv1/v3 FAILs remain historical evidence.

## Purpose and scope

Design persistence for the existing142 typed human-knowledge documents and a separate release
review lane. Address the owner's requirement that casting alone is insufficient: color/year/series/
wheel/tampo may distinguish a release. Do not treat100 unreviewed Wiki rows as verified variants.
Approximately3,000 unique real source release rows are a staged-data goal, not an accuracy promise
or3,000 approved canonical products. This specification does not change final canonical authority.

## Observable requirements

### PVRP-R1 — Preserve approved sources and outputs
WHILE the next stage is designed or built, THE SYSTEM SHALL preserve all existing canonical UUIDs,
source-bound v3/v4 modules/artifacts/protocols, old/new final packs/results and existing review files;
it SHALL NOT remint identities, rewrite approved decisions or retrieve the105 final-v2 questions again.

### PVRP-R2 — Separate stored knowledge from canonical products
WHEN human knowledge is persisted, THE SYSTEM SHALL store100 provisional documents and42 accepted
review-family documents in separate human-knowledge snapshot tables, retain typed IDs/UUIDs/payloads
and provenance, and write zero rows to canonical `product_variant` or canonical index/embedding tables.

### PVRP-R3 — Reject incomplete or mixed snapshots
WHEN an import plan is validated, THE SYSTEM SHALL require the complete142-document approved source
snapshot, source hashes, types, IDs, counts and exclusions before a write; mismatched/duplicate/held
family IDs or mixed source versions SHALL reject the entire plan, not silently discard documents.

### PVRP-R4 — Import atomically and idempotently
WHEN an explicitly authorized import executes in an isolated test database, THE SYSTEM SHALL commit
one validated snapshot transaction or roll back entirely; identical repeat imports SHALL not add rows,
and an existing snapshot ID with different checksum SHALL fail instead of overwrite approved data.

### PVRP-R5 — Fail closed without changing final output
WHEN the optional human-knowledge database profile is unavailable, stale or malformed, THE SYSTEM
SHALL report503/not-ready instead of silently selecting another snapshot; the existing file/offline
default SHALL remain unchanged unless separately selected. Human evidence SHALL remain debug-only.

### PVRP-R6 — Keep storage experiments versioned and measured
WHEN SQL/pgvector retrieval is experimented with, THE SYSTEM SHALL freeze a new protocol/profile
before outputs, preserve casting identity admission/caps/type authority, retain raw query IDs/ranks/
samples/errors and disclose whether startup/SQL/network/indexing are included. Storage roundtrip
parity is not final accuracy; no approximate search or neural-model change SHALL be bundled implicitly.

### PVRP-R7 — Preserve release observations without asserting truth
WHEN a source release is staged, THE SYSTEM SHALL preserve source/revision/row/license/attribution,
raw field values and field-level evidence/status, keep unknown color/year/wheel/tampo values null,
and SHALL NOT infer characteristics from toy number, year-list membership or image filenames.

### PVRP-R8 — Require explicit release-level review
WHEN release approval is proposed, THE SYSTEM SHALL require attributable owner decisions bound to
exact field values/evidence and casting/tool lineage; family approval or initial/human recognition
strings SHALL NOT approve a color/wheel/tampo/release by themselves. Conflicts SHALL remain held.

### PVRP-R9 — Distinguish variants without merging unknowns
WHEN reviewed release drafts are grouped, THE SYSTEM SHALL preserve distinguishable color/year/
series/edition/wheel/tampo variants, record uncertain equivalences as unresolved links, and SHALL
NOT merge records merely because their missing fields compare equal or casting names match.

### PVRP-R10 — Preserve canonical identity evolution boundaries
WHEN additional discriminators require a new identity policy, THE SYSTEM SHALL introduce a new
versioned identity/contract and reviewed mapping for future products; legacy UUIDs and the seven-field
identity policy SHALL stay unchanged. This stage SHALL mint zero new canonical product identities.

### PVRP-R11 — Stage toward scale with honest counters
WHEN collection expands, THE SYSTEM SHALL report raw observations, deduplicated source releases,
castings, unresolved/held releases, reviewed variants, human-knowledge docs and canonical products
separately at100/500/1,500/about3,000 milestones; synthetic padding SHALL NOT meet the real-row goal.

### PVRP-R12 — Recheck access and stop on denial
BEFORE any new remote collection, THE SYSTEM SHALL verify approved endpoints/current access/rights,
freeze a page/revision manifest and request budget, preserve attribution, use serial cached requests,
and stop on401/403/CAPTCHA/robots restrictions. Source-specific rights/access uncertainty SHALL block
collection, not authorize bypass. Images/OCR require a separate source/use/processing approval.

### PVRP-R13 — Validate the actual variant objective separately
BEFORE any canonical variant rollout, THE SYSTEM SHALL obtain a separately approved, output-blind
variant evaluation protocol with exact release labels, same-casting/different-attribute groups,
unknown/conflict/no-match cases, leakage-safe splits and fixed quality/safety/cost gates; the family
final-v2 result SHALL NOT substitute for variant accuracy or train thresholds.

### PVRP-R14 — Keep the first task bounded
WHEN this planning checkpoint is delivered, THE SYSTEM SHALL produce requirements/design/tasks,
source-scope evidence, decisions and narrative log only, with no new source fetch, DB startup/writes,
product-code change or default deployment. Implementation SHALL wait for sequential owner confirmation
of requirements, design and tasks under the Lite G1* gate.

## Not in this approval

Actual3,000-row remote collection; production database writes; canonical release promotion;
automatic photo/color/OCR inference; neural embeddings/approximate vector search; v4 retuning;
modifying the scored final set; changing Human RAG to control canonical answers.
